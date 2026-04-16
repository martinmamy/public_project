import uuid
import urllib.parse
import requests
from decimal import Decimal

from django.conf import settings
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView
from django.utils.crypto import get_random_string
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from MindBridge.services.paypal_services import get_paypal_access_token
from MindBridge.models import PayPalAccount


# =====================================================
# PLATFORM FEES
# =====================================================

BOUNTY_PLATFORM_FEE_PERCENT = Decimal("0.20")   # 20%
TIP_PLATFORM_FEE_PERCENT = Decimal("0.10")      # 10%


def calculate_bounty_payout(amount):
    amount = Decimal(amount)
    fee = amount * BOUNTY_PLATFORM_FEE_PERCENT
    payout = amount - fee
    return payout, fee


def calculate_tip_payout(amount):
    amount = Decimal(amount)
    fee = amount * TIP_PLATFORM_FEE_PERCENT
    payout = amount - fee
    return payout, fee


# =====================================================
# LINK ACCOUNT PAGE
# =====================================================

@method_decorator(login_required, name="dispatch")
class LinkPaymentAccountView(LoginRequiredMixin, TemplateView):
    template_name = "link_account.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_paypal"] = PayPalAccount.objects.filter(user=self.request.user).exists()
        return context


# =====================================================
# START PAYPAL OAUTH
# =====================================================

@method_decorator(login_required, name="dispatch")
class LinkPayPalAccountView(LoginRequiredMixin, View):

    def get(self, request):

        state = get_random_string(32)
        request.session["paypal_oauth_state"] = state

        params = {
            "client_id": settings.PAYPAL_CLIENT_ID,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": settings.PAYPAL_REDIRECT_URI,
            "state": state
        }

        paypal_url = "https://www.paypal.com/signin/authorize?" + urllib.parse.urlencode(params)

        return redirect(paypal_url)


# =====================================================
# PAYPAL CALLBACK
# =====================================================

@method_decorator(login_required, name="dispatch")
class PayPalCallbackView(LoginRequiredMixin, View):

    def get(self, request):

        code = request.GET.get("code")
        state = request.GET.get("state")
        session_state = request.session.get("paypal_oauth_state")

        if not code or state != session_state:
            return redirect("paypal_account_linked_error")

        request.session.pop("paypal_oauth_state", None)

        token_url = "https://api-m.paypal.com/v1/oauth2/token"

        auth = (settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET)

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.PAYPAL_REDIRECT_URI
        }

        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US"
        }

        response = requests.post(token_url, data=data, auth=auth, headers=headers)

        if response.status_code != 200:
            return redirect("paypal_account_linked_error")

        token_data = response.json()

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        if not access_token:
            return redirect("paypal_account_linked_error")

        # Fetch PayPal user info
        userinfo_url = "https://api-m.paypal.com/v1/identity/oauth2/userinfo?schema=paypalv1"

        headers = {"Authorization": f"Bearer {access_token}"}

        userinfo_response = requests.get(userinfo_url, headers=headers)

        if userinfo_response.status_code != 200:
            return redirect("paypal_account_linked_error")

        userinfo = userinfo_response.json()

        paypal_email = userinfo.get("email")
        payer_id = userinfo.get("payer_id")

        if not paypal_email or not payer_id:
            return redirect("paypal_account_linked_error")

        PayPalAccount.objects.update_or_create(
            user=request.user,
            defaults={
                "paypal_email": paypal_email,
                "payer_id": payer_id,
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        )

        return redirect("paypal_account_linked")


# =====================================================
# SUCCESS PAGE
# =====================================================

@method_decorator(login_required, name="dispatch")
class PayPalAccountLinkedView(LoginRequiredMixin, TemplateView):
    template_name = "paypal_success.html"


# =====================================================
# ERROR PAGE
# =====================================================

@method_decorator(login_required, name="dispatch")
class PayPalAccountLinkedErrorView(LoginRequiredMixin, TemplateView):
    template_name = "paypal_error.html"


# =====================================================
# PAYOUT SERVICE
# =====================================================

def send_paypal_payout(receiver: str, amount: float, note="MindBridge payout"):

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
            "email_subject": "You received a payment from MindBridge!"
        },
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {
                "value": str(amount),
                "currency": "USD"
            },
            "receiver": receiver,
            "note": note,
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


# =====================================================
# BOUNTY PAYOUT
# =====================================================

def send_bounty_payout(receiver_email, bounty_amount):

    payout, fee = calculate_bounty_payout(bounty_amount)

    result = send_paypal_payout(
        receiver=receiver_email,
        amount=float(payout),
        note="MindBridge bounty reward"
    )

    return {
        "expert_received": payout,
        "platform_fee": fee,
        "paypal_response": result
    }


# =====================================================
# TIP PAYOUT
# =====================================================

def send_tip_payout(receiver_email, tip_amount):

    payout, fee = calculate_tip_payout(tip_amount)

    result = send_paypal_payout(
        receiver=receiver_email,
        amount=float(payout),
        note="MindBridge tip reward"
    )

    return {
        "expert_received": payout,
        "platform_fee": fee,
        "paypal_response": result
    }