import json
import re
from datetime import timedelta
import uuid
import urllib.parse
from django.template.loader import render_to_string
import requests
from django.conf import settings
from django.shortcuts import redirect
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from MindBridge.models import Problem, Answer, Bounty, User, KnowledgeBaseEntry
from MindBridge.forms import AnswerForm
from MindBridge.services.notification_service import NotificationService
from MindBridge.services.reputation_service import ReputationService
from MindBridge.services.expert_verification_service import ExpertVerificationService
from MindBridge.services.paypal_services import get_paypal_access_token



def send_paypal_payout(receiver: str, amount: float):
    """
    Send a payout to a PayPal email address.
    """
    if float(amount) < 1:
        raise ValueError("Minimum payout amount is $1")

    access_token = get_paypal_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payout_data = {
        "sender_batch_header": {
            "sender_batch_id": str(uuid.uuid4()),
            "email_subject": "You received a bounty from MindBridge!"
        },
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {"value": str(amount), "currency": "USD"},
            "receiver": receiver,
            "note": "MindBridge bounty reward",
            "sender_item_id": str(uuid.uuid4())
        }]
    }

    response = requests.post(
        "https://api-m.paypal.com/v1/payments/payouts",
        headers=headers,
        json=payout_data
    )

    if response.status_code not in [200, 201]:
        raise Exception(f"PayPal payout failed: {response.text}")

    return response.json()


# -----------------------------
# Utility functions
# -----------------------------

def is_api_request(request):
    """Detect if the request expects JSON (API) response."""
    return (
        request.headers.get("Accept") == "application/json" or
        request.headers.get("Content-Type") == "application/json"
    )


def extract_mentions(text):
    """Extract @username mentions from text and return queryset of User objects."""
    usernames = re.findall(r'@([\w-]+)', text or "")
    return User.objects.filter(username__in=usernames)


def serialize_answer(answer):
    """Convert answer to JSON-serializable dict."""
    return {
        "id": str(answer.id),
        "content": answer.content,
        "file": answer.file.url if answer.file else None,
        "author": answer.author.username,
        "votes_score": answer.votes_score,
        "tips_received": float(answer.tips_received),
        "is_accepted": answer.is_accepted,
        "created_at": answer.created_at.isoformat(),
        "updated_at": answer.updated_at.isoformat(),
    }


# =====================================================
# CREATE ANSWER
# =====================================================

@method_decorator(login_required, name="dispatch")
class CreateAnswerView(View):

    def post(self, request, problem_id):

        problem = get_object_or_404(Problem, id=problem_id)

        form = AnswerForm(request.POST, request.FILES)

        if not form.is_valid():

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "errors": form.errors
                }, status=400)

            messages.error(request, "Invalid input.")
            return redirect("problem_detail", problem_id=problem.id)

        with transaction.atomic():

            answer = form.save(commit=False)
            answer.problem = problem
            answer.author = request.user
            answer.save()

            display_name = (
                f"{request.user.first_name} {request.user.last_name}".strip()
                if request.user.first_name or request.user.last_name
                else request.user.username
            )

            # Notify problem owner
            if problem.author != request.user:
                NotificationService.create_notification(
                    user=problem.author,
                    message=f"{display_name} answered your problem '{problem.title}'.",
                    url=f"/problems/{problem.id}/"
                )

            # Mention notifications
            for user in extract_mentions(answer.content):
                if user != request.user and user != problem.author:
                    NotificationService.create_notification(
                        user=user,
                        message=f"{display_name} mentioned you in an answer.",
                        url=f"/problems/{problem.id}/#answer-{answer.id}"
                    )

        # =========================
        # AJAX RESPONSE
        # =========================
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":

            html = render_to_string(
                "partials/answer_card.html",
                {
                    "answer": answer,
                    "user": request.user
                },
                request=request
            )

            return JsonResponse({
                "success": True,
                "html": html,
                "answer_id": answer.id
            })

        # =========================
        # NORMAL RESPONSE
        # =========================
        messages.success(request, "Answer posted successfully.")

        return redirect("problem_detail", problem_id=problem.id)


def generate_ai_answer(request, problem_id):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    problem_obj = get_object_or_404(Problem, id=problem_id)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    user_prompt = data.get("prompt", "").strip()

    problem_text = problem_obj.description

    prompt_text = f"""
Problem:
{problem_text}
"""

    if user_prompt:
        prompt_text += f"\nAdditional context:\n{user_prompt}\n"

    prompt_text += "\nProvide a clear step-by-step solution."

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",

                # 🔥 REQUIRED
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "FancyLearn",
            },
            json={
                "model": "openai/gpt-4o-mini",  # 🔥 much better than Mistral 7B
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert tutor. "
                            "Explain step-by-step in a clear, structured way."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt_text
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 800
            },
            timeout=20
        )

        data = response.json()

        ai_answer = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        return JsonResponse({"answer": ai_answer})

    except Exception as e:
        return JsonResponse({
            "error": "openrouter_failed",
            "details": str(e)
        }, status=500)

# =====================================================
# UPDATE ANSWER
# =====================================================

@method_decorator(login_required, name="dispatch")
class UpdateAnswerView(View):
    """Allows authors to update their answers."""

    def post(self, request, answer_id):
        answer = get_object_or_404(Answer, id=answer_id)

        if answer.author != request.user:
            return JsonResponse({"error": "not_allowed"}, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid_json"}, status=400)

        form = AnswerForm(data, instance=answer)
        
        if not form.is_valid():
            return JsonResponse({
                "success": False,
                "errors": form.errors,
                "message": "Invalid input or inappropriate language."
            }, status=400)

        with transaction.atomic():
            form.save()

        return JsonResponse({"status": "updated", "answer": serialize_answer(answer)})


# =====================================================
# DELETE ANSWER
# =====================================================

@method_decorator(login_required, name="dispatch")
class DeleteAnswerView(View):
    """Allows authors to delete their answers."""

    def post(self, request, answer_id):
        answer = get_object_or_404(Answer, id=answer_id)

        if answer.author != request.user:
            return JsonResponse({"error": "not_allowed"}, status=403)

        problem_id = answer.problem.id
        with transaction.atomic():
            answer.delete()

        if is_api_request(request):
            return JsonResponse({"status": "deleted", "answer_id": str(answer_id)})

        messages.success(request, "Answer deleted successfully.")
        return redirect("problem_detail", problem_id=problem_id)


# =====================================================
# ACCEPT ANSWER
# =====================================================

@method_decorator(login_required, name="dispatch")
class AcceptAnswerView(View):

    def post(self, request, answer_id):

        answer = get_object_or_404(
            Answer.objects.select_related("problem", "author"),
            id=answer_id
        )
        problem = answer.problem

        # --------------------------
        # PERMISSIONS
        # --------------------------
        if problem.author != request.user:
            return JsonResponse({"error": "not_allowed"}, status=403)

        # Already accepted
        if answer.is_accepted:
            if is_api_request(request):
                return JsonResponse({"status": "already_accepted"})
            messages.info(request, "This answer is already accepted.")
            return redirect("problem_detail", problem_id=problem.id)

        # Prevent multiple accepted answers (CRITICAL FIX)
        if Answer.objects.filter(
            problem=problem,
            is_accepted=True
        ).exists():

            if is_api_request(request):
                return JsonResponse(
                    {"error": "answer_already_accepted"},
                    status=400
                )

            messages.error(request, "This problem already has an accepted answer.")
            return redirect("problem_detail", problem_id=problem.id)

        with transaction.atomic():

            # --------------------------
            # ACCEPT ANSWER
            # --------------------------
            answer.is_accepted = True
            answer.save(update_fields=["is_accepted"])

            problem.is_solved = True
            problem.save(update_fields=["is_solved"])

            # --------------------------
            # KNOWLEDGE BASE
            # --------------------------
            kb_entry, created = KnowledgeBaseEntry.objects.get_or_create(
                problem=problem,
                defaults={
                    "answer": answer,
                    "title": problem.title,
                    "description": problem.description,
                    "category": problem.category,
                }
            )

            if not created:
                kb_entry.answer = answer
                kb_entry.title = problem.title
                kb_entry.description = problem.description
                kb_entry.category = problem.category
                kb_entry.save()

            # --------------------------
            # REPUTATION
            # --------------------------
            ReputationService.award_points(
                user=answer.author,
                action="accepted_answer",
                reason="Accepted answer"
            )

            # --------------------------
            # EXPERT VERIFICATION
            # --------------------------
            result = ExpertVerificationService.verify_user(answer.author)

            if result == "verified":
                NotificationService.create_notification(
                    user=answer.author,
                    message="🎉 Congratulations! You are now a Verified Expert.",
                    url=reverse("profile", args=[answer.author.id])
                )

            # --------------------------
            # BOUNTY
            # --------------------------
            bounty = getattr(problem, "bounty", None)

            if bounty and bounty.status == "held":
                bounty.awarded_to = answer.author

                if getattr(answer.author, "paypal_account", None):
                    try:
                        send_paypal_payout(
                            receiver=answer.author.paypal_account.paypal_email,
                            amount=bounty.amount
                        )
                        bounty.status = "awarded"
                    except Exception as e:
                        print(f"PayPal payout failed: {e}")
                else:
                    bounty.expires_at = timezone.now() + timedelta(days=10)

                    NotificationService.create_notification(
                        user=answer.author,
                        message="You won a bounty! Add PayPal within 10 days."
                    )

                bounty.save()

            # --------------------------
            # NOTIFICATION
            # --------------------------
            if answer.author != request.user:
                NotificationService.create_notification(
                    user=answer.author,
                    actor=request.user,
                    message=f"Your answer to '{problem.title}' was accepted!",
                    url=reverse("problem_detail", args=[problem.id])
                )

        # --------------------------
        # RESPONSE
        # --------------------------
        if is_api_request(request):
            return JsonResponse({
                "status": "accepted",
                "answer_id": str(answer.id)
            })

        messages.success(request, "Answer accepted successfully.")
        return redirect("problem_detail", problem_id=problem.id)