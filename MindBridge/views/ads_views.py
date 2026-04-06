from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F

from MindBridge.models import Advertisement, PayPalAccount, Problem
from MindBridge.services.paypal_services import get_paypal_access_token
import requests
import json
from decimal import Decimal


# -----------------------------
# CREATE AD
# -----------------------------
@method_decorator(login_required, name="dispatch")
class CreateAdView(View):
    """
    Handles ad creation:
    - Checks if user has linked PayPal
    - Supports API JSON and web form
    - Calculates total price
    - Creates ad in 'pending' state
    """

    def get(self, request):
        if not hasattr(request.user, "paypal_account"):
            messages.warning(request, "You must link PayPal before creating an ad.")
            return redirect("link_payment_account")
        return render(request, "create_ad.html")

    def post(self, request):
        # PayPal check
        if not hasattr(request.user, "paypal_account"):
            if request.META.get("HTTP_ACCEPT") == "application/json":
                return JsonResponse({"success": False, "error": "Link PayPal first"}, status=403)
            messages.warning(request, "You must link PayPal before creating an ad.")
            return redirect("link_payment_account")

        # -------------------------
        # API JSON REQUEST
        # -------------------------
        if request.META.get("HTTP_ACCEPT") == "application/json":
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "invalid_json"}, status=400)

            url = data.get("target_url")
            duration = int(data.get("duration_days", 7))
            price_per_day = Decimal("2.0")
            total_price = duration * price_per_day

            if not url:
                return JsonResponse({"error": "Missing required fields"}, status=400)

            ad = Advertisement.objects.create(
                advertiser=request.user,
                advertiser_name=request.user.username,
                target_url=url,
                duration_days=duration,
                price=total_price,
                status="pending"
            )

            return JsonResponse({
                "success": True,
                "ad_id": str(ad.id),
                "amount": float(total_price)
            })

        # -------------------------
        # WEB FORM
        # -------------------------
        image = request.FILES.get("image")
        url = request.POST.get("url")
        duration = int(request.POST.get("duration_days", 7))
        price_per_day = Decimal("2.0")
        total_price = duration * price_per_day

        if not url or not image:
            messages.error(request, "Please provide both image and target URL.")
            return render(request, "create_ad.html")

        with transaction.atomic():
            ad = Advertisement.objects.create(
                advertiser=request.user,
                advertiser_name=request.user.username,
                image=image,
                target_url=url,
                duration_days=duration,
                price=total_price,
                status="pending"
            )

        messages.success(request, f"Ad created! Please complete payment of ${total_price} to go live.")
        return redirect("create_ad_payment", ad_id=ad.id)


# -----------------------------
# CREATE AD PAYMENT
# -----------------------------
@method_decorator(login_required, name="dispatch")
class CreateAdPaymentView(View):
    """
    Redirects user to PayPal approval for a pending ad.
    """

    def get(self, request, ad_id):
        ad = get_object_or_404(Advertisement, id=ad_id, advertiser=request.user)

        if ad.status != "pending":
            messages.warning(request, "This ad is already paid or active.")
            return redirect("advertiser_dashboard")

        access_token = get_paypal_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payment_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": str(ad.price)
                }
            }],
            "application_context": {
                "return_url": request.build_absolute_uri(reverse("ad_payment_success", args=[ad.id])),
                "cancel_url": request.build_absolute_uri(reverse("advertiser_dashboard"))
            }
        }

        response = requests.post("https://api-m.paypal.com/v2/checkout/orders", json=payment_data, headers=headers)
        if response.status_code not in [200, 201]:
            messages.error(request, "PayPal payment creation failed.")
            return redirect("advertiser_dashboard")

        data = response.json()
        approve_url = next(link["href"] for link in data["links"] if link["rel"] == "approve")
        return redirect(approve_url)


# -----------------------------
# AD PAYMENT SUCCESS
# -----------------------------
@method_decorator(login_required, name="dispatch")
class AdPaymentSuccessView(View):
    """
    Marks ad as active after successful PayPal payment.
    """

    def get(self, request, ad_id):
        ad = get_object_or_404(Advertisement, id=ad_id, advertiser=request.user)

        if ad.status != "pending":
            messages.warning(request, "This ad is already live.")
            return redirect("advertiser_dashboard")

        now = timezone.now()
        ad.start_at = now
        ad.expires_at = now + timezone.timedelta(days=ad.duration_days)
        ad.status = "active"
        ad.save()

        messages.success(request, "Payment successful! Your ad is now live 🚀")
        return redirect("advertiser_dashboard")


# -----------------------------
# ADVERTISER DASHBOARD
# -----------------------------
@method_decorator(login_required, name="dispatch")
class AdvertiserDashboardView(View):
    template_name = "ads_dashboard.html"

    def get(self, request):
        ads = Advertisement.objects.filter(advertiser=request.user)
        stats = {
            "total_clicks": ads.aggregate(total=Sum("clicks"))["total"] or 0,
            "total_impressions": ads.aggregate(total=Sum("impressions"))["total"] or 0,
            "total_revenue": ads.aggregate(total=Sum("price"))["total"] or 0
        }

        return render(request, self.template_name, {
            "ads": ads,
            "stats": stats
        })


# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
@method_decorator(login_required, name="dispatch")
class AdminAdsDashboardView(View):
    template_name = "ads_dashboard.html"

    def get(self, request):
        if not request.user.is_staff:
            messages.warning(request, "Access denied.")
            return redirect("advertiser_dashboard")

        admin_ads = Advertisement.objects.all()
        admin_stats = {
            "total_clicks": admin_ads.aggregate(total=Sum("clicks"))["total"] or 0,
            "total_impressions": admin_ads.aggregate(total=Sum("impressions"))["total"] or 0,
            "total_revenue": admin_ads.aggregate(total=Sum("price"))["total"] or 0
        }

        return render(request, self.template_name, {
            "admin_ads": admin_ads,
            "admin_stats": admin_stats
        })

@method_decorator(login_required, name="dispatch")
class ProblemAdsView(View):
    """
    Returns ads HTML snippet for a specific problem.
    """
    template_name = "ads_snippet.html"  # your problem ad snippet

    def get(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)

        now = timezone.now()
        # active ads targeting this problem
        ads = Advertisement.objects.filter(
            status="active",
            expires_at__gt=now,
            category=problem
        ).order_by("impressions", "-created_at")[:3]

        # fallback ads if none for problem
        if not ads.exists():
            ads = Advertisement.objects.filter(
                status="active",
                expires_at__gt=now,
                category__isnull=True
            ).order_by("impressions", "-created_at")[:3]

        # increment impressions
        Advertisement.objects.filter(id__in=[ad.id for ad in ads]).update(impressions=F("impressions") + 1)

        return render(request, self.template_name, {"ads": ads})
    
# -----------------------------
# TRACK AD CLICKS
# -----------------------------
@method_decorator(login_required, name="dispatch")
class AdClickView(View):
    """
    Tracks ad clicks (CPC monetization)
    """

    def post(self, request, ad_id):
        updated = Advertisement.objects.filter(id=ad_id).update(clicks=F("clicks") + 1)
        if updated == 0:
            return JsonResponse({"success": False, "error": "Ad not found"}, status=404)
        return JsonResponse({"success": True})