import json
import re, requests
from datetime import timedelta
import uuid
import urllib.parse
import requests
from django.conf import settings


# ====================================================
# PAYPAL SERVICE
# ====================================================
def get_paypal_access_token():
    """
    Fetch OAuth token for server-to-server PayPal API calls.
    """
    url = "https://api-m.paypal.com/v1/oauth2/token"
    response = requests.post(
        url,
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"}
    )
    if response.status_code != 200:
        raise Exception(f"PayPal authentication failed: {response.text}")
    return response.json()["access_token"]


class PayPalClient:

    # =====================================================
    # ACCESS TOKEN
    # =====================================================

    @staticmethod
    def get_access_token():

        url = f"{settings.PAYPAL_BASE_URL}/v1/oauth2/token"

        response = requests.post(
            url,
            auth=(
                settings.PAYPAL_CLIENT_ID,
                settings.PAYPAL_CLIENT_SECRET
            ),
            headers={
                "Accept": "application/json",
                "Accept-Language": "en_US",
            },
            data={
                "grant_type": "client_credentials"
            }
        )

        response.raise_for_status()
        return response.json()["access_token"]

    # =====================================================
    # CREATE SUBSCRIPTION
    # =====================================================

    @classmethod
    def create_subscription(
        cls,
        plan_id,
        return_url,
        cancel_url,
        subscriber_email=None,
    ):

        access_token = cls.get_access_token()

        url = f"{settings.PAYPAL_BASE_URL}/v1/billing/subscriptions"

        payload = {
            "plan_id": plan_id,

            # IMPORTANT: always include subscriber object
            "subscriber": {
                "email_address": subscriber_email
            } if subscriber_email else {},

            # CRITICAL: PayPal expects full context object
            "application_context": {
                "brand_name": "Your Platform",
                "locale": "en-US",
                "user_action": "SUBSCRIBE_NOW",
                "return_url": return_url,
                "cancel_url": cancel_url,
            }
        }

        # remove empty subscriber (prevents PayPal 422 in some cases)
        if not subscriber_email:
            payload.pop("subscriber", None)

        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            json=payload
        )

        # -------------------------------------------------
        # DEBUG SAFETY (VERY IMPORTANT)
        # -------------------------------------------------

        if response.status_code >= 400:

            try:
                error_data = response.json()
            except Exception:
                error_data = response.text

            raise Exception(f"PayPal Error: {error_data}")

        return response.json()

    # =====================================================
    # CANCEL SUBSCRIPTION
    # =====================================================

    @classmethod
    def cancel_subscription(cls, subscription_id, reason="User cancelled"):

        access_token = cls.get_access_token()

        url = (
            f"{settings.PAYPAL_BASE_URL}"
            f"/v1/billing/subscriptions/{subscription_id}/cancel"
        )

        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            json={
                "reason": reason
            }
        )

        # -------------------------------------------------
        # DEBUG SAFETY
        # -------------------------------------------------

        if response.status_code >= 400:

            try:
                error_data = response.json()
            except Exception:
                error_data = response.text

            raise Exception(f"PayPal Cancel Error: {error_data}")

        return True