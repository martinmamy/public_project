import json, re

from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model  # ✅ Use this instead
from django.urls import reverse
from MindBridge.services.notification_service import NotificationService
from django.utils import timezone
from datetime import timedelta
from MindBridge.models import Answer, Tip
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from MindBridge.models import Problem, Bookmark, User, Follow, Bounty, ProblemPromotion
from MindBridge.forms import ProblemForm, AnswerForm, CommentForm
from MindBridge.services.analytics_service import AnalyticsService
from MindBridge.predefined import PREDEFINED_CATEGORIES
from django.db.models import (
    Count,
    Q,
    F,
    Exists,
    OuterRef,
    Value,
    BooleanField,
    IntegerField,
    Case,
    When
)

from MindBridge.util.moderation import contains_bad_words

# Use your custom user model
User = get_user_model()

# -------------------------------------------------
# UTILITY
# -------------------------------------------------

def is_api_request(request):
    return (
        request.headers.get("Accept") == "application/json"
        or request.headers.get("Content-Type") == "application/json"
    )


def serialize_problem(problem):
    post_type = getattr(problem, "post_type", "issue")
    
    # Determine redirect URL for frontend
    if post_type == "information":
        redirect_url = reverse("talenthub")  # Redirect to talenthub page
    else:
        redirect_url = reverse("problem_detail", args=[problem.id])
    
    return {
        "id": str(problem.id),
        "title": problem.title,
        "description": problem.description,
        "author": {
            "id": problem.author.id,
            "username": problem.author.username
        },
        "category": problem.category,
        "tags": [t.strip() for t in (problem.tags or "").split(",") if t.strip()],
        "votes": problem.votes_score,
        "answers": problem.answers.count(),
        "views": problem.views_count,
        "bounty_amount": float(problem.bounty_amount or 0),
        "tips_received": float(problem.tips_received or 0),
        "is_solved": problem.answers.filter(is_accepted=True).exists(),
        "post_type": post_type,
        "created_at": problem.created_at.isoformat(),
        "updated_at": problem.updated_at.isoformat(),
        "file_url": problem.file.url if problem.file else None,
        "redirect_url": redirect_url
    }


# -------------------------------------------------
# CREATE PROBLEM
# -------------------------------------------------

# Regex to detect @username mentions
MENTION_PATTERN = r'@([\w-]+)'

def extract_mentions(text):
    """Return a queryset of users mentioned in the text."""
    usernames = re.findall(MENTION_PATTERN, text)
    return User.objects.filter(username__in=usernames)


# =====================================================
# CREATE PROBLEM
# =====================================================

from decimal import Decimal, InvalidOperation

@method_decorator(login_required, name="dispatch")
class CreateProblemView(LoginRequiredMixin, View):
    template_name = "create_problem.html"
    login_url = "login"

    def get(self, request):
        form = ProblemForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):

        # =====================================================
        # API REQUEST
        # =====================================================
        if request.META.get("HTTP_ACCEPT") == "application/json":

            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "error": "invalid_json"}, status=400)

            title = (data.get("title") or "").strip()
            description = (data.get("description") or "").strip()
            category = data.get("category")
            tags = data.get("tags", [])
            post_type = data.get("post_type", "issue")
            order_id = data.get("paypal_order_id")

            # Safe Decimal parsing
            try:
                bounty_amount = Decimal(str(data.get("bounty_amount", "0")))
            except (InvalidOperation, TypeError):
                bounty_amount = Decimal("0")

            # -----------------------
            # VALIDATION
            # -----------------------
            if not title or not description or not category:
                return JsonResponse({
                    "success": False,
                    "error": "Title, description, and category required"
                }, status=400)

            # 🔥 BAD WORD CHECK (IMPORTANT FIX)
            if contains_bad_words(title) or contains_bad_words(description):
                return JsonResponse({
                    "success": False,
                    "error": "Your post contains inappropriate language."
                }, status=400)

            # PayPal check
            if bounty_amount > 0 and not hasattr(request.user, "paypal_account"):
                return JsonResponse({
                    "success": False,
                    "error": "You must link PayPal before creating a bounty."
                }, status=403)

            with transaction.atomic():

                problem = Problem.objects.create(
                    author=request.user,
                    title=title,
                    description=description,
                    category=category,
                    bounty_amount=bounty_amount if hasattr(request.user, "paypal_account") else Decimal("0"),
                    tags=",".join(tags),
                    post_type=post_type
                )

                # Bounty
                if bounty_amount > 0 and order_id and hasattr(request.user, "paypal_account"):
                    Bounty.objects.create(
                        problem=problem,
                        creator=request.user,
                        amount=bounty_amount,
                        status="held",
                        paypal_order_id=order_id,
                        expires_at=timezone.now() + timedelta(days=10)
                    )

                # Admin notifications
                admins = User.objects.filter(is_staff=True)
                if admins.exists():
                    NotificationService.create_notification(
                        users=admins,
                        actor=request.user,
                        message=f"New problem posted by {request.user.username}: '{problem.title}'",
                        url=reverse("problem_detail", args=[problem.id])
                    )

                # Mentions
                for user in extract_mentions(description):
                    if user != request.user:
                        NotificationService.create_notification(
                            user=user,
                            actor=request.user,
                            message=f"{request.user.username} mentioned you in a problem description.",
                            url=reverse("problem_detail", args=[problem.id])
                        )

            return JsonResponse({
                "success": True,
                "problem": serialize_problem(problem)
            })

        # =====================================================
        # WEB REQUEST (Already Safe via Form)
        # =====================================================
        form = ProblemForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, {"form": form})

        bounty_amount = form.cleaned_data.get("bounty_amount") or Decimal("0")
        post_type = form.cleaned_data.get("post_type", "issue")

        # PayPal check
        if bounty_amount > 0 and not hasattr(request.user, "paypal_account"):
            messages.warning(
                request,
                "You must link your PayPal account before creating a bounty."
            )
            return redirect("link_payment_account")

        with transaction.atomic():

            problem = form.save(commit=False)
            problem.author = request.user

            tags_str = form.cleaned_data.get("tags_input", "")
            problem.tags = ",".join(
                t.strip() for t in tags_str.split(",") if t.strip()
            )

            problem.post_type = post_type
            problem.save()

            # Bounty
            if bounty_amount > 0 and hasattr(request.user, "paypal_account"):
                Bounty.objects.create(
                    problem=problem,
                    creator=request.user,
                    amount=bounty_amount,
                    status="held",
                    expires_at=timezone.now() + timedelta(days=10)
                )

            # Admin notifications
            admins = User.objects.filter(is_staff=True)
            if admins.exists():
                NotificationService.create_notification(
                    users=admins,
                    actor=request.user,
                    message=f"New problem posted by {request.user.username}: '{problem.title}'",
                    url=reverse("problem_detail", args=[problem.id])
                )

            # Mentions
            for user in extract_mentions(problem.description):
                if user != request.user:
                    NotificationService.create_notification(
                        user=user,
                        actor=request.user,
                        message=f"{request.user.username} mentioned you in a problem description.",
                        url=reverse("problem_detail", args=[problem.id])
                    )

        messages.success(request, "Problem created successfully.")

        # Redirect based on post type
        if post_type == "information":
            return redirect("talenthub")

        return redirect("problem_detail", problem_id=problem.id)

# =====================================================
# UPDATE PROBLEM
# =====================================================

from decimal import Decimal, InvalidOperation

@method_decorator(login_required, name="dispatch")
class UpdateProblemView(LoginRequiredMixin, View):
    login_url = "login"

    def get_object(self, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)
        if problem.author != self.request.user:
            raise PermissionError
        return problem

    def post(self, request, problem_id):

        # -----------------------
        # PERMISSION CHECK
        # -----------------------
        try:
            problem = self.get_object(problem_id)
        except PermissionError:
            return JsonResponse({"success": False, "error": "permission_denied"}, status=403)

        # -----------------------
        # PARSE JSON
        # -----------------------
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "invalid_json"}, status=400)

        updated = False

        # -----------------------
        # 🔥 VALIDATION (IMPORTANT FIX)
        # -----------------------
        title = data.get("title", problem.title)
        description = data.get("description", problem.description)

        if contains_bad_words(title) or contains_bad_words(description):
            return JsonResponse({
                "success": False,
                "error": "Your post contains inappropriate language."
            }, status=400)

        # Safe bounty parsing
        if "bounty_amount" in data:
            try:
                data["bounty_amount"] = Decimal(str(data["bounty_amount"]))
            except (InvalidOperation, TypeError):
                return JsonResponse({
                    "success": False,
                    "error": "Invalid bounty amount"
                }, status=400)

        # -----------------------
        # UPDATE
        # -----------------------
        with transaction.atomic():

            allowed_fields = ["title", "description", "bounty_amount"]

            for field in allowed_fields:
                if field in data:
                    setattr(problem, field, data[field])
                    updated = True

            if "category_id" in data:
                problem.category_id = data["category_id"]
                updated = True

            if "tags" in data:
                problem.tags = ",".join(
                    [t.strip() for t in data["tags"] if t.strip()]
                )
                updated = True

            if updated:
                problem.save()

                # -----------------------
                # Mentions (only if description updated)
                # -----------------------
                if "description" in data:
                    mentioned_users = extract_mentions(problem.description)
                    for user in mentioned_users:
                        if user != request.user:
                            NotificationService.create_notification(
                                user=user,
                                actor=request.user,
                                message=f"{request.user.username} mentioned you in an updated problem description.",
                                url=reverse("problem_detail", args=[problem.id])
                            )

        return JsonResponse({
            "success": True,
            "status": "updated",
            "problem": serialize_problem(problem)
        })


# -------------------------------------------------
# DELETE PROBLEM
# -------------------------------------------------

@method_decorator(login_required, name="dispatch")
class DeleteProblemView(LoginRequiredMixin, View):
    login_url = "login"

    def post(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)

        # Permission check
        if problem.author != request.user and not request.user.is_staff:
            return JsonResponse({"error": "Permission denied"}, status=403)

        try:
            with transaction.atomic():
                problem.delete()
        except Exception as e:
            # For AJAX: return JSON
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"error": str(e)}, status=500)
            # For normal requests: redirect with message
            messages.error(request, f"Error deleting problem: {e}")
            return redirect("list_problems")

        # If AJAX request, return JSON
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})

        # Normal POST request: redirect to list page with success message
        messages.success(request, "Problem deleted successfully.")
        return redirect("list_problems")
    
# -------------------------------------------------
# PROBLEM DETAIL
# -------------------------------------------------

@method_decorator(login_required, name="dispatch")
class ProblemDetailView(View):
    template_name = "problem_detail.html"

    def get(self, request, problem_id):
        now = timezone.now()

        # -------------------------------------------------
        # FETCH PROBLEM
        # -------------------------------------------------
        problem = get_object_or_404(
            Problem.objects.select_related("author")
            .prefetch_related("answers__author", "comments__user"),
            id=problem_id
        )

        # -------------------------------------------------
        # TRACK ANALYTICS
        # -------------------------------------------------
        AnalyticsService.track_problem_view(
            problem=problem,
            user=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        # -------------------------------------------------
        # CHECK PAYPAL LINK
        # -------------------------------------------------
        has_paypal = hasattr(request.user, "paypal_account")
        user_balance = getattr(request.user, "wallet_balance", 0)  # example attribute

        # -------------------------------------------------
        # ACTIVE BOUNTY
        # -------------------------------------------------
        active_bounty = (
            Bounty.objects.filter(
                problem=problem,
                status="held",
                expires_at__gt=now
            )
            .order_by("-created_at")
            .first()
        )

        # -------------------------------------------------
        # ACTIVE PROMOTION
        # -------------------------------------------------
        active_promotion = (
            ProblemPromotion.objects.filter(
                problem=problem,
                expires_at__gt=now
            )
            .order_by("-expires_at")
            .first()
        )

        # -------------------------------------------------
        # CAN USER ADD BOUNTY?
        # -------------------------------------------------
        can_add_bounty = (
            request.user == problem.author
            and not active_bounty
            and has_paypal
        )

        # -------------------------------------------------
        # CAN USER PROMOTE PROBLEM?
        # -------------------------------------------------
        # Determine available promotion types
        PROMOTION_PRICES = {
            "featured": 3,
            "boosted": 7,
            "pinned": 15
        }

        # Only allow promotion if user is author, has PayPal, has enough balance,
        # and no active promotion of that type
        active_promotions = ProblemPromotion.objects.filter(
            problem=problem,
            user=request.user,
            expires_at__gt=now
        ).values_list("promotion_type", flat=True)

        can_promote_types = []
        for p_type, price in PROMOTION_PRICES.items():
            if (
                request.user == problem.author
                and has_paypal
                and user_balance >= price
                and p_type not in active_promotions
            ):
                can_promote_types.append(p_type)

        # -------------------------------------------------
        # FORMS
        # -------------------------------------------------
        answer_form = AnswerForm()
        comment_form = CommentForm()

        # -------------------------------------------------
        # TRENDING PROBLEMS
        # -------------------------------------------------
        trending_problems = (
            Problem.objects.select_related("author")
            .order_by("-views_count", "-votes_score")[:5]
        )

        # -------------------------------------------------
        # TAGS
        # -------------------------------------------------
        tags_list = [t.strip() for t in problem.tags.split(",")] if problem.tags else []

        # -------------------------------------------------
        # API RESPONSE
        # -------------------------------------------------
        if is_api_request(request):
            return JsonResponse(
                serialize_problem(
                    problem,
                    extra={
                        "has_paypal": has_paypal,
                        "can_add_bounty": can_add_bounty,
                        "active_bounty": active_bounty.id if active_bounty else None,
                        "active_promotion": active_promotion.id if active_promotion else None,
                        "can_promote_types": can_promote_types,
                        "user_balance": user_balance,
                    }
                )
            )

        # -------------------------------------------------
        # TEMPLATE SELECTION
        # -------------------------------------------------
        if is_api_request(request):
            return JsonResponse(
                serialize_problem(
                    problem,
                    extra={
                        "has_paypal": has_paypal,
                        "can_add_bounty": can_add_bounty,
                        "active_bounty": active_bounty.id if active_bounty else None,
                        "active_promotion": active_promotion.id if active_promotion else None,
                        "can_promote_types": can_promote_types,
                        "user_balance": user_balance,
                    }
                )
            )

        # detect modal request
        is_modal = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        template = (
            "problem_detail_partial.html"
            if is_modal
            else "problem_detail.html"
        )

        context = {
            "problem": problem,
            "tags_list": tags_list,
            "answers": problem.answers.all(),
            "answer_form": answer_form,
            "comment_form": comment_form,
            "trending_problems": trending_problems,

            "has_paypal": has_paypal,
            "active_bounty": active_bounty,
            "active_promotion": active_promotion,
            "can_add_bounty": can_add_bounty,
            "can_promote_types": can_promote_types,
            "user_balance": user_balance,
        }

        return render(request, template, context)



@method_decorator(login_required, name="dispatch")
class ListProblemsView(View):

    template_name = "list_problems.html"
    paginate_by = 20

    def get(self, request):

        user = request.user if request.user.is_authenticated else None

        # -------------------------------------------------
        # QUERY PARAMS
        # -------------------------------------------------
        category = request.GET.get("category")
        sort = request.GET.get("sort", "recent")
        search = request.GET.get("search", "").strip()

        # -------------------------------------------------
        # BASE QUERY (only issues)
        # -------------------------------------------------
        problems_qs = (
            Problem.objects.filter(post_type="issue")  # <-- only issues
            .select_related("author")
            .prefetch_related("answers")
            .annotate(
                # COUNTS
                annot_answers_count=Count("answers", distinct=True),
                annot_votes_score=F("votes_score"),
                annot_views_count=F("views_count"),
                annot_accepted_count=Count(
                    "answers",
                    filter=Q(answers__is_accepted=True)
                ),
                # PROMOTION PRIORITY
                promotion_priority=Case(
                    When(
                        promotions__promotion_type="pinned",
                        promotions__expires_at__gt=timezone.now(),
                        then=Value(3)
                    ),
                    When(
                        promotions__promotion_type="boosted",
                        promotions__expires_at__gt=timezone.now(),
                        then=Value(2)
                    ),
                    When(
                        promotions__promotion_type="featured",
                        promotions__expires_at__gt=timezone.now(),
                        then=Value(1)
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                # BOOKMARK
                is_bookmarked=(
                    Exists(
                        Bookmark.objects.filter(
                            user=user,
                            problem=OuterRef("pk")
                        )
                    ) if user else Value(False, output_field=BooleanField())
                ),
                # FOLLOW
                is_following=(
                    Exists(
                        Follow.objects.filter(
                            follower=user,
                            following=OuterRef("author")
                        )
                    ) if user else Value(False, output_field=BooleanField())
                ),
            )
        )

        # -------------------------------------------------
        # FILTERING
        # -------------------------------------------------
        if category:
            problems_qs = problems_qs.filter(category=category)
        if search:
            problems_qs = problems_qs.filter(title__icontains=search)

        # -------------------------------------------------
        # ORDERING
        # -------------------------------------------------
        ordering = ["-promotion_priority"]
        if sort == "votes":
            ordering.append("-votes_score")
        elif sort == "answers":
            ordering.append("-annot_answers_count")
        else:  # recent
            ordering.append("-created_at")
        problems_qs = problems_qs.order_by(*ordering)

        # -------------------------------------------------
        # PAGINATION
        # -------------------------------------------------
        paginator = Paginator(problems_qs, self.paginate_by)
        page_number = request.GET.get("page", 1)
        page = paginator.get_page(page_number)

        # -------------------------------------------------
        # BOOKMARK SIDEBAR
        # -------------------------------------------------
        bookmarked_problems = problems_qs.filter(is_bookmarked=True)[:10] if user else []

        # -------------------------------------------------
        # SOLVED FLAG
        # -------------------------------------------------
        for problem in page:
            problem.is_solved = problem.annot_accepted_count > 0

        # -------------------------------------------------
        # API RESPONSE
        # -------------------------------------------------
        if is_api_request(request):
            return JsonResponse({
                "results": [serialize_problem(p) for p in page],
                "pagination": {
                    "page": page.number,
                    "pages": paginator.num_pages,
                    "has_next": page.has_next(),
                    "has_previous": page.has_previous(),
                    "total": paginator.count,
                },
            })

        # -------------------------------------------------
        # TEMPLATE
        # -------------------------------------------------
        return render(
            request,
            self.template_name,
            {
                "problems": page,
                "bookmarked_problems": bookmarked_problems,
                "PREDEFINED_CATEGORIES": PREDEFINED_CATEGORIES,
                "current_category": category,
                "current_sort": sort,
                "current_search": search,
            },
        )
        
        
@method_decorator(login_required, name="dispatch")
class TalentHubView(View):
    template_name = "talenthub.html"
    paginate_by = 20

    def get(self, request):
        user = request.user if request.user.is_authenticated else None

        # -------------------------------------------------
        # QUERY PARAMS
        # -------------------------------------------------
        category = request.GET.get("category")
        sort = request.GET.get("sort", "recent")
        search = request.GET.get("search", "").strip()

        # -------------------------------------------------
        # BASE QUERY (only information posts)
        # -------------------------------------------------
        problems_qs = (
            Problem.objects.filter(post_type="information")  # <-- only information
            .select_related("author")
            .prefetch_related("answers")
            .annotate(
                # Counts
                annot_answers_count=Count("answers", distinct=True),
                annot_votes_score=F("votes_score"),
                annot_views_count=F("views_count"),
                annot_accepted_count=Count(
                    "answers",
                    filter=Q(answers__is_accepted=True)
                ),
                # Promotion priority
                promotion_priority=Case(
                    When(
                        promotions__promotion_type="pinned",
                        promotions__expires_at__gt=timezone.now(),
                        then=Value(3)
                    ),
                    When(
                        promotions__promotion_type="boosted",
                        promotions__expires_at__gt=timezone.now(),
                        then=Value(2)
                    ),
                    When(
                        promotions__promotion_type="featured",
                        promotions__expires_at__gt=timezone.now(),
                        then=Value(1)
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                # Bookmark
                is_bookmarked=Exists(
                    Bookmark.objects.filter(user=user, problem=OuterRef("pk"))
                ) if user else Value(False, output_field=BooleanField()),
                # Following
                is_following=Exists(
                    Follow.objects.filter(follower=user, following=OuterRef("author"))
                ) if user else Value(False, output_field=BooleanField()),
            )
        )

        # -------------------------------------------------
        # FILTERING
        # -------------------------------------------------
        if category:
            problems_qs = problems_qs.filter(category=category)
        if search:
            problems_qs = problems_qs.filter(title__icontains=search)

        # -------------------------------------------------
        # ORDERING
        # -------------------------------------------------
        ordering = ["-promotion_priority"]
        if sort == "votes":
            ordering.append("-votes_score")
        elif sort == "answers":
            ordering.append("-annot_answers_count")
        else:  # recent
            ordering.append("-created_at")
        problems_qs = problems_qs.order_by(*ordering)

        # -------------------------------------------------
        # PAGINATION
        # -------------------------------------------------
        paginator = Paginator(problems_qs, self.paginate_by)
        page_number = request.GET.get("page", 1)
        infos_page = paginator.get_page(page_number)

        # -------------------------------------------------
        # BOOKMARK SIDEBAR
        # -------------------------------------------------
        bookmarked_problems = problems_qs.filter(is_bookmarked=True)[:10] if user else []

        # -------------------------------------------------
        # SOLVED FLAG
        # -------------------------------------------------
        for problem in infos_page:
            problem.is_solved = problem.annot_accepted_count > 0

        # -------------------------------------------------
        # API RESPONSE (optional)
        # -------------------------------------------------
        if is_api_request(request):
            return JsonResponse({
                "information": [serialize_problem(p) for p in infos_page],
                "pagination": {
                    "information": {
                        "page": infos_page.number,
                        "pages": paginator.num_pages,
                        "has_next": infos_page.has_next(),
                        "has_previous": infos_page.has_previous(),
                        "total": paginator.count,
                    },
                },
            })

        # -------------------------------------------------
        # TEMPLATE RENDER
        # -------------------------------------------------
        return render(
            request,
            self.template_name,
            {
                "information": infos_page,
                "bookmarked_problems": bookmarked_problems,
                "PREDEFINED_CATEGORIES": PREDEFINED_CATEGORIES,
                "current_category": category,
                "current_sort": sort,
                "current_search": search,
            },
        )
        
        
def get_problem_answers(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)

    answers = problem.answers.select_related("author").order_by("-votes_score")

    data = []
    for a in answers:
        data.append({
            "id": str(a.id),
            "author": a.author.username,
            "author_id": str(a.author.id),
            "avatar": a.author.avatar.url if a.author.avatar else "",
            "content": a.content,
            "votes": a.votes_score,
            "tips": a.tips_received,
            "is_accepted": a.is_accepted,
            "file": a.file.url if a.file else "",
        })

    return JsonResponse({"answers": data})

# -------------------------------------------------
# TRENDING PROBLEMS
# -------------------------------------------------

class TrendingProblemsView(View):
    template_name = "trending_problems.html"

    def get(self, request):
        queryset = Problem.objects.order_by("-votes_score", "-views_count")[:50]

        if is_api_request(request):
            return JsonResponse({"results": [serialize_problem(p) for p in queryset]})

        return render(request, self.template_name, {"problems": queryset})


# -------------------------------------------------
# BOOKMARK
# -------------------------------------------------

@login_required
@require_POST
def toggle_bookmark(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, problem=problem)

    if not created:
        bookmark.delete()
        return JsonResponse({"status": "unsaved"})

    return JsonResponse({"status": "saved"})


@login_required
@require_POST
def toggle_talenthub_bookmark(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, problem=problem)

    if not created:
        bookmark.delete()
        return JsonResponse({"status": "unsaved"})

    return JsonResponse({"status": "saved"})

@method_decorator(login_required, name="dispatch")
class SendTipView(View):
    """
    AJAX endpoint to send tips to an answer.
    """
    def post(self, request, answer_id):
        answer = get_object_or_404(Answer, id=answer_id)
        user = request.user

        try:
            data = json.loads(request.body)
            amount = float(data.get("amount", 0))
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid tip amount"}, status=400)

        if amount <= 0:
            return JsonResponse({"error": "Tip must be greater than zero"}, status=400)

        if answer.author == user:
            return JsonResponse({"error": "You cannot tip your own answer"}, status=403)

        with transaction.atomic():
            Tip.objects.create(
                sender=user,
                receiver=answer.author,
                answer=answer,
                amount=amount
            )
            answer.tips_received = F("tips_received") + amount
            answer.save(update_fields=["tips_received"])

        answer.refresh_from_db()  # Ensure latest tips_received value
        return JsonResponse({"success": True, "tips_received": float(answer.tips_received)})
    
    
    
@method_decorator(login_required, name="dispatch")
class PromoteProblemView(LoginRequiredMixin, View):

    PROMOTION_PRICES = {
        "featured": 3,
        "boosted": 7,
        "pinned": 15
    }

    PROMOTION_DURATION = {
        "featured": 1,  # days
        "boosted": 3,
        "pinned": 7
    }

    def post(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id, author=request.user)
        user = request.user

        promotion_type = request.POST.get("promotion_type")
        if promotion_type not in self.PROMOTION_PRICES:
            messages.error(request, "Invalid promotion type.")
            return redirect("problem_detail", problem_id=problem.id)

        # ----------------------------
        # CHECK PAYPAL LINK
        # ----------------------------
        if not hasattr(user, "paypal_account"):
            messages.warning(request, "You must link your PayPal account to promote a problem.")
            return redirect("link_payment_account")

        # ----------------------------
        # CHECK USER BALANCE
        # ----------------------------
        price = self.PROMOTION_PRICES[promotion_type]
        if getattr(user, "wallet_balance", 0) < price:
            messages.warning(request, "Insufficient balance to promote this problem.")
            return redirect("problem_detail", problem_id=problem.id)

        # ----------------------------
        # CHECK ACTIVE PROMOTION
        # ----------------------------
        now = timezone.now()
        existing_promo = ProblemPromotion.objects.filter(
            problem=problem,
            promotion_type=promotion_type,
            expires_at__gt=now
        ).first()

        if existing_promo:
            messages.info(request, f"This problem already has an active '{promotion_type}' promotion.")
            return redirect("problem_detail", problem_id=problem.id)

        # ----------------------------
        # CREATE PROMOTION
        # ----------------------------
        duration = self.PROMOTION_DURATION[promotion_type]
        ProblemPromotion.objects.create(
            problem=problem,
            user=user,
            promotion_type=promotion_type,
            price=price,
            expires_at=now + timedelta(days=duration)
        )

        # ----------------------------
        # DEDUCT USER BALANCE
        # ----------------------------
        user.wallet_balance -= price
        user.save(update_fields=["wallet_balance"])

        messages.success(request, f"Your problem is now promoted as '{promotion_type}'!")
        return redirect("problem_detail", problem_id=problem.id)