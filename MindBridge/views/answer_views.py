import json
import re
from datetime import timedelta
import uuid
import urllib.parse
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
    """Handles posting an answer with optional media and mentions."""

    def post(self, request, problem_id):
        if not request.user.is_authenticated:
            if is_api_request(request):
                return JsonResponse({"error": "Authentication required"}, status=401)
            messages.error(request, "You must be logged in to answer.")
            return redirect("login")

        problem = get_object_or_404(Problem, id=problem_id)
        form = AnswerForm(request.POST, request.FILES)

        if not form.is_valid():
            if is_api_request(request):
                return JsonResponse({
                    "success": False,
                    "errors": form.errors
                }, status=400)

            messages.error(request, "Invalid input or inappropriate language.")
            return redirect("problem_detail", problem_id=problem.id)

        # ✅ ONLY SAVE AFTER VALIDATION PASSES
        with transaction.atomic():
            answer = form.save(commit=False)
            answer.problem = problem
            answer.author = request.user
            answer.save()

            # Notify problem owner
            if problem.author != request.user:
                NotificationService.create_notification(
                    user=problem.author,
                    message=f"{request.user.username} answered your problem '{problem.title}'.",
                    url=f"/problems/{problem.id}/"
                )

            # Notify mentioned users
            for user in extract_mentions(answer.content):
                if user != request.user and user != problem.author:
                    NotificationService.create_notification(
                        user=user,
                        message=f"{request.user.username} mentioned you in an answer.",
                        url=f"/problems/{problem.id}/#answer-{answer.id}"
                    )

        if is_api_request(request):
            return JsonResponse({"status": "success", "answer": serialize_answer(answer)})

        messages.success(request, "Answer posted successfully.")
        return redirect("problem_detail", problem_id=problem.id)



def generate_ai_answer(request, problem_id):
    if request.method == "POST":
        problem_obj = get_object_or_404(Problem, id=problem_id)

        # Use the correct field here
        problem_text = problem_obj.description  # <-- fixed

        data = json.loads(request.body)
        user_prompt = data.get("prompt", "")
        prompt_text = f"Problem: {problem_text}\n"
        if user_prompt:
            prompt_text += f"Additional context: {user_prompt}\n"
        prompt_text += "Provide a detailed, clear, step-by-step answer."

        # Call OpenRouter API
        openrouter_api_key = settings.OPENROUTER_API_KEY
        url = "https://api.openrouter.ai/v1/completions"
        payload = {
            "model": "gpt-4.1-mini",
            "prompt": prompt_text,
            "max_tokens": 500,
        }
        headers = {"Authorization": f"Bearer {openrouter_api_key}"}

        try:
            r = requests.post(url, json=payload, headers=headers)
            r.raise_for_status()
            result = r.json()
            ai_answer = result["choices"][0]["text"].strip()
        except Exception as e:
            print(e)
            ai_answer = ""

        return JsonResponse({"answer": ai_answer})

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
    """
    Allows problem author to accept an answer,
    award reputation, verify expert status,
    and handle bounty payouts.
    """

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

        if answer.is_accepted:
            return JsonResponse({"status": "already_accepted"})

        with transaction.atomic():
            # --------------------------
            # ACCEPT ANSWER
            # --------------------------
            answer.is_accepted = True
            answer.save(update_fields=["is_accepted"])

            problem.is_solved = True
            problem.save(update_fields=["is_solved"])

            # --------------------------
            # KNOWLEDGE BASE CREATION
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
            # Corrected: must pass action, optional points
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
            # BOUNTY HANDLING
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
                        message="You won a bounty! Link your PayPal within 10 days to receive it."
                    )
                bounty.save()

            # --------------------------
            # NOTIFICATIONS
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
            return JsonResponse({"status": "accepted", "answer_id": str(answer.id)})

        messages.success(request, "Answer accepted successfully.")
        return redirect("problem_detail", problem_id=problem.id)