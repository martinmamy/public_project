import json
import re
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