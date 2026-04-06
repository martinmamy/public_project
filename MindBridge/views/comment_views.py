import uuid
import json
from django.core.paginator import Paginator
from django.views import View
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
import json, re
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from MindBridge.models import Comment, Problem, Answer, User
from MindBridge.forms import CommentForm
from MindBridge.services.notification_service import NotificationService


# Regex to detect @username mentions
MENTION_PATTERN = r'@([\w-]+)'

def extract_mentions(text):
    """Return a queryset of users mentioned in the text."""
    usernames = re.findall(MENTION_PATTERN, text)
    return User.objects.filter(username__in=usernames)


# =====================================================
# CREATE COMMENT
# =====================================================

@method_decorator(login_required, name="dispatch")
class CreateCommentView(LoginRequiredMixin, View):

    def post(self, request):
        content = request.POST.get("content", "").strip()
        problem_id = request.POST.get("problem_id")
        answer_id = request.POST.get("answer_id")

        if not content:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "Comment cannot be empty."})
            messages.error(request, "Comment cannot be empty.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        comment = Comment(user=request.user, content=content)

        if problem_id:
            problem = get_object_or_404(Problem, id=uuid.UUID(problem_id))
            comment.problem = problem
        elif answer_id:
            answer = get_object_or_404(Answer.objects.select_related("problem"), id=uuid.UUID(answer_id))
            comment.answer = answer
            comment.problem = answer.problem
            problem = answer.problem
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "Invalid comment target."})
            messages.error(request, "Invalid comment target.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        with transaction.atomic():
            comment.save()

            # ✅ FIX: dynamic URL
            if comment.problem.post_type == "information":
                base_url = reverse("talenthub") + f"#problem-{comment.problem.id}"
            else:
                base_url = reverse("problem_detail", args=[comment.problem.id])

            comment_url = f"{base_url}#comment-{comment.id}"

            # -----------------------
            # Notifications
            # -----------------------
            if comment.problem.author != request.user:
                NotificationService.create_notification(
                    user=comment.problem.author,
                    actor=request.user,
                    message=f"{request.user.username} commented on your problem '{comment.problem.title}'.",
                    url=base_url
                )

            if comment.answer and comment.answer.author != request.user and comment.answer.author != comment.problem.author:
                NotificationService.create_notification(
                    user=comment.answer.author,
                    actor=request.user,
                    message=f"{request.user.username} commented on your answer.",
                    url=base_url
                )

            # Mentions
            mentioned_users = extract_mentions(comment.content)
            for user in mentioned_users:
                if user != request.user and user != comment.problem.author and (not comment.answer or user != comment.answer.author):
                    NotificationService.create_notification(
                        user=user,
                        actor=request.user,
                        message=f"{request.user.username} mentioned you in a comment.",
                        url=comment_url  # ✅ FIXED
                    )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "comment": {
                    "id": str(comment.id),
                    "user": request.user.username,
                    "user_id": request.user.id,
                    "user_avatar": request.user.avatar.url if getattr(request.user, 'avatar', None) else None,
                    "user_initial": request.user.username[0].upper(),
                    "content": comment.content,
                    "created_at": comment.created_at.isoformat()
                },
                "current_user_id": request.user.id
            })

        messages.success(request, "Comment posted successfully.")

        # ✅ FIX redirect too
        if comment.problem.post_type == "information":
            return redirect("talenthub")
        return redirect("problem_detail", problem_id=comment.problem.id)

# =====================================================
# EDIT PROBLEM COMMENT
# =====================================================

@method_decorator(login_required, name="dispatch")
class EditProblemCommentView(LoginRequiredMixin, View):

    def post(self, request, comment_id):
        comment = get_object_or_404(
            Comment.objects.select_related("problem"),
            id=comment_id,
            problem__isnull=False
        )

        if comment.user != request.user:
            return JsonResponse({"error": "permission_denied"}, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid_json"}, status=400)

        form = CommentForm(data, instance=comment)
        if not form.is_valid():
            return JsonResponse({"error": "invalid_data", "errors": form.errors}, status=400)

        with transaction.atomic():
            updated = form.save(commit=False)
            updated.user = request.user
            updated.save(update_fields=["content"])

            # ✅ FIX: dynamic URL
            if updated.problem.post_type == "information":
                base_url = reverse("talenthub") + f"#problem-{updated.problem.id}"
            else:
                base_url = reverse("problem_detail", args=[updated.problem.id])

            comment_url = f"{base_url}#comment-{updated.id}"

            # Mentions
            mentioned_users = extract_mentions(updated.content)
            for user in mentioned_users:
                if user != request.user and user != updated.problem.author:
                    NotificationService.create_notification(
                        user=user,
                        actor=request.user,
                        message=f"{request.user.username} mentioned you in an updated comment.",
                        url=comment_url  # ✅ FIXED
                    )

        return JsonResponse({
            "status": "updated",
            "content": updated.content
        })


# =====================================================
# EDIT ANSWER COMMENT
# =====================================================

@method_decorator(login_required, name="dispatch")
class EditAnswerCommentView(LoginRequiredMixin, View):
    def post(self, request, comment_id):
        comment = get_object_or_404(Comment.objects.select_related("answer__problem"), id=comment_id, answer__isnull=False)

        if comment.user != request.user:
            return JsonResponse({"error": "permission_denied"}, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid_json"}, status=400)

        form = CommentForm(data, instance=comment)
        if not form.is_valid():
            return JsonResponse({"error": "invalid_data", "errors": form.errors}, status=400)

        with transaction.atomic():
            updated = form.save(commit=False)
            updated.user = request.user
            updated.save(update_fields=["content"])

            # Notify newly mentioned users
            mentioned_users = extract_mentions(updated.content)
            problem_url = reverse("problem_detail", args=[updated.answer.problem.id])
            for user in mentioned_users:
                if user != request.user and user != updated.answer.author and user != updated.answer.problem.author:
                    NotificationService.create_notification(
                        user=user,
                        actor=request.user,
                        message=f"{request.user.username} mentioned you in an updated comment.",
                        url=f"{problem_url}#comment-{updated.id}"
                    )

        return JsonResponse({"status": "updated", "content": updated.content})


# =====================================================
# DELETE PROBLEM COMMENT
# =====================================================

@method_decorator(login_required, name="dispatch")
class DeleteProblemCommentView(LoginRequiredMixin, View):

    def post(self, request, comment_id):
        try:
            comment = get_object_or_404(
                Comment.objects.select_related("problem"),
                id=comment_id,
                problem__isnull=False
            )

            if comment.user != request.user and not request.user.is_staff:
                return JsonResponse({"error": "permission_denied"}, status=403)

            comment.delete()
            return JsonResponse({"status": "deleted", "comment_id": str(comment_id)})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# =====================================================
# DELETE ANSWER COMMENT
# =====================================================

@method_decorator(login_required, name="dispatch")
class DeleteAnswerCommentView(LoginRequiredMixin, View):
    """
    Delete a comment belonging to an answer
    """

    def post(self, request, comment_id):

        comment = get_object_or_404(
            Comment.objects.select_related("answer__problem"),
            id=uuid.UUID(comment_id),
            answer__isnull=False
        )

        if comment.user != request.user and not request.user.is_staff:
            return JsonResponse({"error": "permission_denied"}, status=403)

        comment.delete()

        return JsonResponse({
            "status": "deleted",
            "comment_id": str(comment_id)
        })


# =====================================================
# LIST COMMENTS FOR A PROBLEM
# =====================================================

@method_decorator(login_required, name="dispatch")
class ProblemCommentsView(View):
    """
    Paginated comments for a problem
    """

    template_name = "problem_comments.html"

    def get(self, request, problem_id):

        problem = get_object_or_404(
            Problem,
            id=uuid.UUID(problem_id)
        )

        comments = (
            Comment.objects
            .filter(problem=problem)
            .select_related("user")
            .order_by("created_at")
        )

        paginator = Paginator(comments, 20)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(request, self.template_name, {
            "problem": problem,
            "comments": page_obj,
            "form": CommentForm()
        })


# =====================================================
# LIST COMMENTS FOR AN ANSWER
# =====================================================

@method_decorator(login_required, name="dispatch")
class AnswerCommentsView(View):
    """
    Paginated comments for an answer
    """

    template_name = "answer_comments.html"

    def get(self, request, answer_id):

        answer = get_object_or_404(
            Answer.objects.select_related("problem"),
            id=uuid.UUID(answer_id)
        )

        comments = (
            Comment.objects
            .filter(answer=answer)
            .select_related("user")
            .order_by("created_at")
        )

        paginator = Paginator(comments, 20)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(request, self.template_name, {
            "answer": answer,
            "comments": page_obj,
            "form": CommentForm()
        })