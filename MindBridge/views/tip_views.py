import uuid
import json
import requests

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.db import transaction
from django.db.models import F
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from MindBridge.models import Answer, Problem, Tip, Payment, PayPalAccount
from MindBridge.services.paypal_services import get_paypal_access_token


def send_paypal_payout(receiver_email: str, amount: float):
    """
    Send a payout to a PayPal account by email.
    """
    if float(amount) < 1:
        raise ValueError("Minimum payout amount is $1")

    access_token = get_paypal_access_token()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    payout_data = {
        "sender_batch_header": {
            "sender_batch_id": str(uuid.uuid4()),
            "email_subject": "You received a MindBridge bounty!"
        },
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {"value": str(amount), "currency": "USD"},
            "receiver": receiver_email,
            "note": "MindBridge bounty reward",
            "sender_item_id": str(uuid.uuid4())
        }]
    }

    response = requests.post(
        "https://api-m.paypal.com/v1/payments/payouts",
        json=payout_data,
        headers=headers
    )

    if response.status_code not in [200, 201]:
        raise Exception(f"PayPal payout failed: {response.text}")
    return response.json()


# ====================================================
# TIP A PROBLEM
# ====================================================
@method_decorator(login_required, name="dispatch")
class SendProblemTipView(View):
    def post(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)
        user = request.user

        if not hasattr(user, "paypal_account"):
            return JsonResponse({"error": "Link your PayPal account first."}, status=403)

        try:
            data = json.loads(request.body)
            amount = float(data.get("amount", 0))
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid tip amount."}, status=400)

        if amount <= 0:
            return JsonResponse({"error": "Tip must be greater than zero."}, status=400)
        if problem.author == user:
            return JsonResponse({"error": "Cannot tip your own problem."}, status=403)

        with transaction.atomic():
            # Record tip
            Tip.objects.create(sender=user, receiver=problem.author, problem=problem, amount=amount)
            problem.tips_received = F("tips_received") + amount
            problem.save(update_fields=["tips_received"])

            # Optional: instant PayPal payout to problem author
            if hasattr(problem.author, "paypal_account"):
                try:
                    send_paypal_payout(problem.author.paypal_account.paypal_email, amount)
                except Exception as e:
                    print("PayPal payout error:", e)

        problem.refresh_from_db()
        return JsonResponse({"success": True, "tips_received": float(problem.tips_received)})


# ====================================================
# TIP AN ANSWER
# ====================================================
@method_decorator(login_required, name="dispatch")
class SendTipView(View):
    def post(self, request, answer_id):
        answer = get_object_or_404(Answer, id=answer_id)
        user = request.user

        if not hasattr(user, "paypal_account"):
            return JsonResponse({"error": "Link your PayPal account first."}, status=403)

        try:
            data = json.loads(request.body)
            amount = float(data.get("amount", 0))
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid tip amount."}, status=400)

        if amount <= 0:
            return JsonResponse({"error": "Tip must be greater than zero."}, status=400)
        if answer.author == user:
            return JsonResponse({"error": "Cannot tip your own answer."}, status=403)

        with transaction.atomic():
            # Record tip
            Tip.objects.create(sender=user, receiver=answer.author, answer=answer, amount=amount)
            answer.tips_received = F("tips_received") + amount
            answer.save(update_fields=["tips_received"])

            # Optional: instant PayPal payout to answer author
            if hasattr(answer.author, "paypal_account"):
                try:
                    send_paypal_payout(answer.author.paypal_account.paypal_email, amount)
                except Exception as e:
                    print("PayPal payout error:", e)

        answer.refresh_from_db()
        return JsonResponse({"success": True, "tips_received": float(answer.tips_received)})


# ====================================================
# CREATE PAYPAL ORDER (OPTIONAL FRONTEND CAPTURE FLOW)
# ====================================================

@method_decorator(login_required, name="dispatch")
class CreateTipOrderView(LoginRequiredMixin, View):
    def post(self, request, answer_id):
        if not hasattr(request.user, "paypal_account"):
            return JsonResponse({"error": "Link PayPal first"}, status=403)

        answer = get_object_or_404(Answer, id=answer_id)
        data = json.loads(request.body)
        amount = data.get("amount")

        access_token = get_paypal_access_token()
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}

        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": "USD", "value": str(amount)}}]
        }

        response = requests.post("https://api-m.paypal.com/v2/checkout/orders", json=order_data, headers=headers)
        if response.status_code not in [200, 201]:
            return JsonResponse({"error": "Failed to create PayPal order"}, status=400)

        return JsonResponse({"orderID": response.json().get("id")})


@method_decorator(login_required, name="dispatch")
class CaptureTipPaymentView(LoginRequiredMixin, View):
    def post(self, request, answer_id):
        data = json.loads(request.body)
        order_id = data.get("orderID")
        amount = data.get("amount")

        answer = get_object_or_404(Answer, id=answer_id)
        access_token = get_paypal_access_token()
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}

        capture_url = f"https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture"
        response = requests.post(capture_url, headers=headers)

        if response.status_code != 201:
            return JsonResponse({"error": "Payment failed"}, status=400)

        with transaction.atomic():
            Tip.objects.create(sender=request.user, receiver=answer.author, answer=answer, amount=amount)
            Payment.objects.create(user=request.user, amount=amount, payment_type="tip", reference_id=order_id, status="completed")

        return JsonResponse({"status": "success"})