import json
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from MindBridge.forms import RegisterForm, LoginForm, UpdateProfileForm
from MindBridge.models import UserProfile, Problem, Answer, Bounty, Tip, Follow
from django.db.models import Sum
from MindBridge.services.expert_verification_service import ExpertVerificationService
from MindBridge.services.reputation_service import ReputationService

User = get_user_model()


# ---------------------------
# REGISTER VIEW
# ---------------------------

class RegisterView(View):
    template_name = "register.html"

    def get(self, request):
        form = RegisterForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        try:
            data = json.loads(request.body)
            form = RegisterForm(data)
        except Exception:
            form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)

            if request.content_type == "application/json":
                return JsonResponse({"status": "registered"})
            return redirect(reverse("login"))

        errors = form.errors.get_json_data()
        if request.content_type == "application/json":
            return JsonResponse({"errors": errors}, status=400)

        return render(request, self.template_name, {"form": form})


# ---------------------------
# LOGIN VIEW
# ---------------------------

class LoginView(View):
    template_name = "login.html"

    def get(self, request):
        form = LoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        try:
            data = json.loads(request.body)
            form = LoginForm(data)
        except Exception:
            form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)

            if user:
                login(request, user)
                if request.content_type == "application/json":
                    return JsonResponse({"status": "logged_in"})
                return redirect(reverse("list_problems"))

            form.add_error(None, "Invalid username or password")

        errors = form.errors.get_json_data()
        if request.content_type == "application/json":
            return JsonResponse({"errors": errors}, status=400)

        return render(request, self.template_name, {"form": form})

# ---------------------------
# PROFILE VIEW
# ---------------------------

@method_decorator(login_required, name="dispatch")
class ProfileView(View):
    template_name = "profile.html"

    def get(self, request, user_id):
        user_obj = get_object_or_404(User, id=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=user_obj)

        # Check if logged-in user follows this profile
        is_following = False
        if request.user.is_authenticated and request.user != user_obj:
            is_following = Follow.objects.filter(
                follower=request.user,
                following=user_obj
            ).exists()

        # TOTAL TIPS RECEIVED (answers + problems)
        total_tips = Tip.objects.filter(
            receiver=user_obj
        ).aggregate(total=Sum("amount"))["total"] or 0
        
        total_bounties = Problem.objects.filter(
            answers__is_accepted=True,
            answers__author=user_obj
        ).aggregate(total=Sum("bounty_amount"))["total"] or 0

        # Calculate tier dynamically
        tier = ReputationService.calculate_tier(getattr(user_obj, "reputation_score", 0))
        
        status = ExpertVerificationService.eligibility_status(request.user)
        
        profile_data = {
            "username": user_obj.username,
            "email": user_obj.email if request.user == user_obj else None,
            "reputation_score": getattr(user_obj, "reputation_score", 0),
            "tier": tier,   # <-- include tier here
            "is_verified_expert": getattr(user_obj, "is_verified_expert", False),
            "profession": profile.profession,
            "country": profile.country,
            "website": profile.website,
            "bio": getattr(user_obj, "bio", ""),
            "followers_count": profile.followers_count,
            "following_count": profile.following_count,
            "avatar_url": user_obj.avatar.url if getattr(user_obj, "avatar", None) else None,
            "is_owner": request.user == user_obj,
            "is_following": is_following,

            # earnings
            "total_tips_received": total_tips,
            "total_bounties_earned": total_bounties,
        }

        return render(request, self.template_name, {
            "profile_user": user_obj,
            "profile": profile_data,
            "status": status,
        })
        
        
# ---------------------------
# PROFILE ACTIVITY API
# ---------------------------

@method_decorator(login_required, name="dispatch")
class ProfileActivityAPI(View):
    """
    Returns paginated JSON for user's activity.
    Supports types: problems, answers, bounties, tips.
    Bounties and tips are only visible to the profile owner.
    """

    def get(self, request, user_id):

        user_obj = get_object_or_404(User, id=user_id)

        activity_type = request.GET.get("type", "problems")
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 5))

        items = []

        # ---------------------------
        # Problems
        # ---------------------------
        if activity_type == "problems":

            qs = Problem.objects.filter(
                author=user_obj
            ).order_by("-created_at")

            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(page)

            items = [{
                "title": p.title or "Untitled",
                "url": f"/problems/{p.id}/",
                "date": p.created_at.strftime("%b %d, %Y"),
                "votes": p.votes_score or 0,
                "answers": p.answers_count or 0,
                "views": p.views_count or 0,
            } for p in page_obj]

        # ---------------------------
        # Answers
        # ---------------------------
        elif activity_type == "answers":

            qs = Answer.objects.select_related(
                "problem"
            ).filter(
                author=user_obj
            ).order_by("-created_at")

            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(page)

            items = [{
                "problemTitle": a.problem.title if a.problem else "Untitled",
                "problemUrl": f"/problems/{a.problem.id}/" if a.problem else "#",
                "content": a.content or "",
                "date": a.created_at.strftime("%b %d, %Y"),
            } for a in page_obj]

        # ---------------------------
        # Bounties (owner only)
        # ---------------------------
        elif activity_type == "bounties":

            if request.user != user_obj:
                return JsonResponse({"items": []})

            qs = Problem.objects.select_related(
                "author"
            ).filter(
                answers__is_accepted=True,
                answers__author=user_obj
            ).order_by("-created_at").distinct()

            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(page)

            items = [{
                "problemTitle": p.title if p.title else "Untitled",
                "problemUrl": f"/problems/{p.id}/",
                "amount": float(getattr(p, "bounty_amount", 0)),
                "date": p.created_at.strftime("%b %d, %Y"),
            } for p in page_obj]

        # ---------------------------
        # Tips (owner only)
        # ---------------------------
        elif activity_type == "tips":

            if request.user != user_obj:
                return JsonResponse({"items": []})

            qs = Tip.objects.select_related(
                "problem",
                "answer"
            ).filter(
                receiver=user_obj
            ).order_by("-created_at")

            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(page)

            items = [{
                "problemTitle": (
                    t.problem.title if t.problem else
                    t.answer.problem.title if t.answer else
                    "Untitled"
                ),
                "problemUrl": (
                    f"/problems/{t.problem.id}/" if t.problem else
                    f"/problems/{t.answer.problem.id}/" if t.answer else
                    "#"
                ),
                "answerContent": t.answer.content if t.answer else "",
                "amount": float(t.amount),
                "date": t.created_at.strftime("%b %d, %Y"),
            } for t in page_obj]

        return JsonResponse({
            "items": items
        })
        
# ---------------------------

@method_decorator(login_required, name="dispatch")
class UpdateProfileView(View):
    template_name = "update_profile.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect(reverse("login"))

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        initial_data = {"bio": getattr(request.user, "bio", "")}
        form = UpdateProfileForm(instance=profile, initial=initial_data)

        return render(request, self.template_name, {
            "form": form,
            "avatar_url": request.user.avatar.url if request.user.avatar else None
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect(reverse("login"))

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form = UpdateProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            updated_profile = form.save(commit=False)

            # Update User fields
            request.user.bio = form.cleaned_data.get("bio", getattr(request.user, "bio", ""))

            # Handle avatar upload on User model
            avatar_file = form.cleaned_data.get("avatar")
            if avatar_file:
                img = Image.open(avatar_file)
                img = img.convert("RGBA")
                img.thumbnail((300, 300))

                buffer = BytesIO()
                img.save(buffer, format="PNG")
                buffer.seek(0)

                filename = f"{request.user.username}_avatar.png"
                request.user.avatar.save(filename, ContentFile(buffer.read()), save=False)

            # Save both User and UserProfile
            request.user.save()
            updated_profile.save()

            # Redirect to profile with user_id
            return redirect("profile", user_id=request.user.id)

        return render(request, self.template_name, {
            "form": form,
            "avatar_url": request.user.avatar.url if request.user.avatar else None
        })
        
# ---------------------------
# LOGOUT VIEW
# ---------------------------

@method_decorator(login_required, name="dispatch") 
class LogoutView(View):
    def get(self, request):
        logout(request)
        if request.content_type == "application/json":
            return JsonResponse({"status": "logged_out"})
        return redirect(reverse("login"))