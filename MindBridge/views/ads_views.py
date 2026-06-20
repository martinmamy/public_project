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

import json
import requests
from decimal import Decimal

from MindBridge.context_processors import Count
from MindBridge.models import Advertisement, Problem
from MindBridge.services.paypal_services import get_paypal_access_token


# ============================================================
# CREATE AD
# ============================================================

@method_decorator(login_required, name="dispatch")
class CreateAdView(View):
    """
    Create Advertisement
    Supports:
    - Web form
    - JSON API
    - Recurring ads
    - Draft ads
    - Scheduled ads
    """

    template_name = "create_ad.html"

    PRICE_PER_DAY = Decimal("2.00")

    # ==========================================
    # GET
    # ==========================================
    def get(self, request):

        if not hasattr(request.user, "paypal_account"):

            messages.warning(
                request,
                "Link your PayPal account before creating advertisements."
            )

            return redirect("link_payment_account")

        context = {
            "recurring_choices": [3, 7, 14, 30]
        }

        return render(
            request,
            self.template_name,
            context
        )

    # ==========================================
    # POST
    # ==========================================
    def post(self, request):

        # ======================================
        # PAYPAL CHECK
        # ======================================
        if not hasattr(request.user, "paypal_account"):

            if request.content_type == "application/json":

                return JsonResponse(
                    {
                        "success": False,
                        "error": "paypal_not_linked"
                    },
                    status=403
                )

            messages.error(
                request,
                "You must link a PayPal account first."
            )

            return redirect("link_payment_account")

        # ======================================
        # JSON API MODE
        # ======================================
        if request.content_type == "application/json":

            try:
                data = json.loads(request.body)

            except json.JSONDecodeError:

                return JsonResponse(
                    {
                        "success": False,
                        "error": "invalid_json"
                    },
                    status=400
                )

            return self.handle_json_request(
                request,
                data
            )

        # ======================================
        # WEB FORM MODE
        # ======================================
        return self.handle_web_request(request)

    # ======================================================
    # JSON HANDLER
    # ======================================================
    def handle_json_request(self, request, data):

        title = data.get("title")
        description = data.get("description")

        url = data.get("target_url")

        ad_category = data.get("ad_category", "Technology")

        duration = int(data.get("duration_days", 7))

        status = data.get("status", "pending")

        is_recurring = data.get("is_recurring", False)

        recurring_days = int(
            data.get("recurring_days", duration)
        )

        # ======================================
        # VALIDATION
        # ======================================
        if not title:

            return JsonResponse(
                {
                    "success": False,
                    "error": "missing_title"
                },
                status=400
            )

        if not description:

            return JsonResponse(
                {
                    "success": False,
                    "error": "missing_description"
                },
                status=400
            )

        if not url:

            return JsonResponse(
                {
                    "success": False,
                    "error": "missing_target_url"
                },
                status=400
            )

        # ======================================
        # PRICE
        # ======================================
        total_price = self.PRICE_PER_DAY * duration

        # ======================================
        # DATES
        # ======================================
        now = timezone.now()

        start_at = now if status != "draft" else None

        expires_at = (
            now + timezone.timedelta(days=duration)
            if status != "draft"
            else None
        )

        # ======================================
        # CREATE
        # ======================================
        with transaction.atomic():

            ad = Advertisement.objects.create(

                advertiser=request.user,

                advertiser_name=request.user.username,

                title=title,

                description=description,

                ad_category=ad_category,

                target_url=url,

                duration_days=duration,

                price=total_price,

                start_at=start_at,

                expires_at=expires_at,

                status=status,

                # =========================
                # NEW MODEL FIELDS
                # =========================
                is_recurring=is_recurring,

                recurring_days=recurring_days,

                relaunch_count=0,

                stop_recurring=False,

                is_deleted=False,
            )

        return JsonResponse({

            "success": True,

            "ad_id": str(ad.id),

            "status": ad.status,

            "duration_days": ad.duration_days,

            "recurring": ad.is_recurring,

            "recurring_days": ad.recurring_days,

            "amount": float(total_price),

            "expires_at": ad.expires_at,
        })

    # ======================================================
    # WEB FORM HANDLER
    # ======================================================
    def handle_web_request(self, request):

        title = request.POST.get("title")

        description = request.POST.get("description")

        ad_category = request.POST.get(
            "ad_category",
            "Technology"
        )

        ads_file = request.FILES.get("ads_file")

        url = request.POST.get("target_url")

        duration = int(
            request.POST.get("duration_days", 7)
        )

        status = request.POST.get(
            "status",
            "pending"
        )

        # ======================================
        # RECURRING
        # ======================================
        is_recurring = (
            request.POST.get("is_recurring") == "on"
        )

        recurring_days = int(
            request.POST.get(
                "recurring_days",
                duration
            )
        )

        # ======================================
        # VALIDATION
        # ======================================
        if not title:

            messages.error(
                request,
                "Advertisement title is required."
            )

            return render(
                request,
                self.template_name
            )

        if not description:

            messages.error(
                request,
                "Advertisement description is required."
            )

            return render(
                request,
                self.template_name
            )

        if not ads_file:

            messages.error(
                request,
                "Advertisement ads_file is required."
            )

            return render(
                request,
                self.template_name
            )

        if not url:

            messages.error(
                request,
                "Advertisement target URL is required."
            )

            return render(
                request,
                self.template_name
            )

        # ======================================
        # PRICE
        # ======================================
        total_price = self.PRICE_PER_DAY * duration

        # ======================================
        # DATES
        # ======================================
        now = timezone.now()

        start_at = now if status != "draft" else None

        expires_at = (
            now + timezone.timedelta(days=duration)
            if status != "draft"
            else None
        )

        # ======================================
        # CREATE AD
        # ======================================
        with transaction.atomic():

            ad = Advertisement.objects.create(

                advertiser=request.user,

                advertiser_name=request.user.username,

                title=title,

                description=description,

                ad_category=ad_category,

                ads_file=ads_file,

                target_url=url,

                duration_days=duration,

                price=total_price,

                start_at=start_at,

                expires_at=expires_at,

                status=status,

                # =========================
                # NEW FIELDS
                # =========================
                is_recurring=is_recurring,

                recurring_days=recurring_days,

                relaunch_count=0,

                stop_recurring=False,

                is_deleted=False,
            )

        # ======================================
        # SUCCESS
        # ======================================
        if status == "draft":

            messages.success(
                request,
                "Advertisement draft saved successfully."
            )

            return redirect("ads_dashboard")

        messages.success(
            request,
            f"Advertisement created successfully. "
            f"Total spending: ${total_price}"
        )

        return redirect(
            "create_ad_payment",
            ad_id=ad.id
        )


# ============================================================
# PAYPAL PAYMENT INIT
# ============================================================
@method_decorator(login_required, name="dispatch")
class CreateAdPaymentView(View):

    def get(self, request, ad_id):
        ad = get_object_or_404(Advertisement, id=ad_id, advertiser=request.user)

        if ad.status != "pending":
            messages.warning(request, "Ad already processed.")
            return redirect("ads_dashboard")

        token = get_paypal_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": str(ad.price)
                }
            }],
            "application_context": {
                "return_url": request.build_absolute_uri(
                    reverse("ad_payment_success", args=[ad.id])
                ),
                "cancel_url": request.build_absolute_uri(
                    reverse("ads_dashboard")
                )
            }
        }

        res = requests.post(
            "https://api-m.paypal.com/v2/checkout/orders",
            json=payload,
            headers=headers
        )

        if res.status_code not in (200, 201):
            messages.error(request, "Payment initiation failed.")
            return redirect("ads_dashboard")

        approve_url = next(
            link["href"] for link in res.json()["links"]
            if link["rel"] == "approve"
        )

        return redirect(approve_url)


# ============================================================
# PAYMENT SUCCESS
# ============================================================
@method_decorator(login_required, name="dispatch")
class AdPaymentSuccessView(View):

    def get(self, request, ad_id):
        ad = get_object_or_404(Advertisement, id=ad_id, advertiser=request.user)

        if ad.status != "pending":
            return redirect("ads_dashboard")

        now = timezone.now()

        ad.start_at = now
        ad.expires_at = now + timezone.timedelta(days=ad.duration_days)
        ad.status = "active"
        ad.save()

        messages.success(request, "Ad is now live 🚀")
        return redirect("ads_dashboard")


# ============================================================
# ADVERTISER DASHBOARD
# ============================================================

@method_decorator(login_required, name="dispatch")
class AdvertiserDashboardView(View):

    template_name = "ads_dashboard.html"

    # =====================================================
    # STATUS NORMALIZER (REAL-TIME FIX)
    # =====================================================
    def get_effective_status(self, ad):
        now = timezone.now()

        if ad.is_deleted:
            return "deleted"

        if ad.expires_at and ad.expires_at <= now:
            return "expired"

        return ad.status

    # =====================================================
    # EXPIRY INTELLIGENCE (NEW FIX)
    # =====================================================
    def get_expiry_flags(self, ad):
        """
        Dynamically computes:
        - is_expiring_soon (e.g. <= 24h or 2 days)
        - is_urgent_expiry (e.g. <= 6 hours)
        """

        now = timezone.now()

        ad.is_expiring_soon = False
        ad.is_urgent_expiry = False

        if not ad.expires_at:
            return ad

        if ad.expires_at <= now:
            return ad

        remaining = ad.expires_at - now

        # URGENT: less than 6 hours
        if remaining <= timedelta(hours=6):
            ad.is_urgent_expiry = True
            ad.is_expiring_soon = True

        # SOON: less than 48 hours
        elif remaining <= timedelta(days=2):
            ad.is_expiring_soon = True

        return ad

    # =====================================================
    # CTR CALC
    # =====================================================
    def calculate_ctr(self, ad):
        try:
            return round(
                (float(ad.clicks) / float(ad.impressions)) * 100,
                2
            ) if ad.impressions else 0.0
        except (ZeroDivisionError, TypeError, ValueError):
            return 0.0

    # =====================================================
    # CTR LABEL
    # =====================================================
    def get_ctr_level(self, ctr):
        if ctr >= 10:
            return "Excellent"
        elif ctr >= 5:
            return "Good"
        elif ctr >= 2:
            return "Average"
        elif ctr > 0:
            return "Low"
        return "No Traffic"

    # =====================================================
    # GET
    # =====================================================
    def get(self, request):

        # =====================================================
        # BASE ADS
        # =====================================================
        base_ads = Advertisement.objects.filter(
            advertiser=request.user,
            is_deleted=False
        ).order_by("-created_at")

        enriched_ads = []

        # =====================================================
        # ENRICH ADS (STATUS + CTR + EXPIRY FLAGS)
        # =====================================================
        for ad in base_ads:

            ad.ctr = self.calculate_ctr(ad)
            ad.ctr_level = self.get_ctr_level(ad.ctr)
            ad.effective_status = self.get_effective_status(ad)

            # 🔥 NEW: expiry intelligence
            ad = self.get_expiry_flags(ad)

            enriched_ads.append(ad)

        # =====================================================
        # FILTERS (BASED ON EFFECTIVE STATUS)
        # =====================================================
        active_ads = [a for a in enriched_ads if a.effective_status == "active"]
        pending_ads = [a for a in enriched_ads if a.effective_status == "pending"]
        draft_ads = [a for a in enriched_ads if a.effective_status == "draft"]
        expired_ads = [a for a in enriched_ads if a.effective_status == "expired"]
        rejected_ads = [a for a in enriched_ads if a.effective_status == "rejected"]

        # =====================================================
        # GLOBAL STATS
        # =====================================================
        stats_raw = base_ads.aggregate(
            clicks=Sum("clicks"),
            impressions=Sum("impressions"),
            spending=Sum("price"),
        )

        clicks = stats_raw["clicks"] or 0
        impressions = stats_raw["impressions"] or 0
        spending = stats_raw["spending"] or 0

        global_ctr = round((clicks / impressions) * 100, 2) if impressions else 0.0

        stats = {
            "clicks": clicks,
            "impressions": impressions,
            "spending": spending,
            "ctr": global_ctr,
        }

        # =====================================================
        # TAB STATS BUILDER
        # =====================================================
        def build_stats(ad_list):

            clicks = sum(a.clicks for a in ad_list)
            impressions = sum(a.impressions for a in ad_list)
            spending = sum(a.price for a in ad_list)

            ctr = round((clicks / impressions) * 100, 2) if impressions else 0.0

            return {
                "count": len(ad_list),
                "clicks": clicks,
                "impressions": impressions,
                "spending": spending,
                "ctr": ctr,
                "ctr_level": self.get_ctr_level(ctr),
            }

        # =====================================================
        # TAB STATS
        # =====================================================
        tab_stats = {
            "all": build_stats(enriched_ads),
            "active": build_stats(active_ads),
            "pending": build_stats(pending_ads),
            "draft": build_stats(draft_ads),
            "expired": build_stats(expired_ads),
            "rejected": build_stats(rejected_ads),
        }

        # =====================================================
        # TOP ADS
        # =====================================================
        top_ads = sorted(enriched_ads, key=lambda x: x.ctr, reverse=True)[:10]

        # =====================================================
        # RETURN
        # =====================================================
        return render(request, self.template_name, {
            "all_ads": enriched_ads,
            "active_ads": active_ads,
            "pending_ads": pending_ads,
            "draft_ads": draft_ads,
            "expired_ads": expired_ads,
            "rejected_ads": rejected_ads,
            "stats": stats,
            "tab_stats": tab_stats,
            "top_ads": top_ads,
        })


# ============================================================
# ADMIN ADS DASHBOARD
# ============================================================

@method_decorator(login_required, name="dispatch")
class AdminAdsDashboardView(View):

    template_name = "admin_ads_dashboard.html"

    # =====================================================
    # EFFECTIVE STATUS (CRITICAL FIX)
    # =====================================================
    def get_effective_status(self, ad):
        now = timezone.now()

        if ad.is_deleted:
            return "deleted"

        if ad.expires_at and ad.expires_at < now:
            return "expired"

        return ad.status

    # =====================================================
    # CTR CALC
    # =====================================================
    def calculate_ctr(self, ad):
        try:
            return round(
                (float(ad.clicks) / float(ad.impressions)) * 100,
                2
            ) if ad.impressions else 0.0
        except (ZeroDivisionError, TypeError, ValueError):
            return 0.0

    # =====================================================
    # PERFORMANCE LABEL
    # =====================================================
    def get_ctr_level(self, ctr):
        if ctr >= 10:
            return "Excellent"
        elif ctr >= 5:
            return "Good"
        elif ctr >= 2:
            return "Average"
        elif ctr > 0:
            return "Low"
        return "No Traffic"

    # =====================================================
    # GET
    # =====================================================
    def get(self, request):

        if not request.user.is_staff:
            messages.error(request, "Access denied.")
            return redirect("ads_dashboard")

        now = timezone.now()

        # =====================================================
        # OPTIONAL: AUTO EXPIRE CLEANUP (KEEP BUT NOT REQUIRED)
        # =====================================================
        Advertisement.objects.filter(
            status="active",
            expires_at__lt=now
        ).update(status="expired")

        # =====================================================
        # BASE QUERYSET
        # =====================================================
        qs = Advertisement.objects.select_related(
            "advertiser",
            "related_problem"
        ).order_by("-created_at")

        # =====================================================
        # ENRICH ADS (FIXED STATUS + CTR)
        # =====================================================
        ads = []

        for ad in qs:
            ad.ctr = self.calculate_ctr(ad)
            ad.ctr_level = self.get_ctr_level(ad.ctr)
            ad.effective_status = self.get_effective_status(ad)
            ads.append(ad)

        # =====================================================
        # FIXED TAB FILTERS (USE EFFECTIVE STATUS)
        # =====================================================
        active_ads = [a for a in ads if a.effective_status == "active"]
        pending_ads = [a for a in ads if a.effective_status == "pending"]
        draft_ads = [a for a in ads if a.effective_status == "draft"]
        expired_ads = [a for a in ads if a.effective_status == "expired"]
        rejected_ads = [a for a in ads if a.effective_status == "rejected"]

        # =====================================================
        # GLOBAL STATS (UNCHANGED BUT SAFE)
        # =====================================================
        global_stats = qs.aggregate(
            clicks=Sum("clicks"),
            impressions=Sum("impressions"),
            revenue=Sum("price"),
            count=Count("id"),
        )

        clicks = global_stats["clicks"] or 0
        impressions = global_stats["impressions"] or 0
        revenue = global_stats["revenue"] or 0

        global_ctr = round((clicks / impressions) * 100, 2) if impressions else 0.0

        global_stats = {
            "clicks": clicks,
            "impressions": impressions,
            "revenue": revenue,
            "count": global_stats["count"] or 0,
            "ctr": global_ctr,
            "ctr_level": self.get_ctr_level(global_ctr),
        }

        # =====================================================
        # TAB STATS (FIXED USING LISTS)
        # =====================================================
        def calculate_stats(ad_list):

            clicks = sum(a.clicks for a in ad_list)
            impressions = sum(a.impressions for a in ad_list)
            revenue = sum(a.price for a in ad_list)

            ctr = round((clicks / impressions) * 100, 2) if impressions else 0.0

            return {
                "count": len(ad_list),
                "clicks": clicks,
                "impressions": impressions,
                "revenue": revenue,
                "ctr": ctr,
                "ctr_level": self.get_ctr_level(ctr),
            }

        tab_stats = {
            "all": calculate_stats(ads),
            "active": calculate_stats(active_ads),
            "pending": calculate_stats(pending_ads),
            "draft": calculate_stats(draft_ads),
            "expired": calculate_stats(expired_ads),
            "rejected": calculate_stats(rejected_ads),
        }

        # =====================================================
        # TOP ADS
        # =====================================================
        top_ads = sorted(ads, key=lambda x: x.ctr, reverse=True)[:10]

        # =====================================================
        # CONTEXT
        # =====================================================
        return render(request, self.template_name, {
            "is_admin": True,

            # ADS
            "all_ads": ads,
            "active_ads": active_ads,
            "pending_ads": pending_ads,
            "draft_ads": draft_ads,
            "expired_ads": expired_ads,
            "rejected_ads": rejected_ads,

            # GLOBAL STATS
            "global_stats": global_stats,

            # TAB STATS
            "tab_stats": tab_stats,

            # TOP ADS
            "top_ads": top_ads,

            # TIME
            "now": now,
        })
    
# ============================================================
# ADS FOR A PROBLEM (FIXED)
# ============================================================
@method_decorator(login_required, name="dispatch")
class ProblemAdsView(View):

    template_name = "ads_snippet.html"

    def get(self, request, problem_id):

        problem = get_object_or_404(
            Problem,
            id=problem_id
        )

        now = timezone.now()

        # =====================================================
        # PRIMARY ADS
        # =====================================================
        ads = Advertisement.objects.filter(
            related_problem=problem,
            status="active",
            expires_at__gt=now,
            is_deleted=False
        ).order_by(
            "impressions",
            "-created_at"
        )

        # =====================================================
        # FALLBACK GLOBAL ADS
        # =====================================================
        if not ads.exists():

            ads = Advertisement.objects.filter(
                related_problem__isnull=True,
                status="active",
                expires_at__gt=now,
                is_deleted=False
            ).order_by(
                "impressions",
                "-created_at"
            )

        # =====================================================
        # NO ADS → RETURN EMPTY RESPONSE
        # =====================================================
        if not ads.exists():

            return JsonResponse({
                "success": False,
                "html": ""
            })

        # =====================================================
        # UPDATE IMPRESSIONS
        # =====================================================
        ad_ids = ads.values_list(
            "id",
            flat=True
        )

        Advertisement.objects.filter(
            id__in=ad_ids
        ).update(
            impressions=F("impressions") + 1
        )

        # =====================================================
        # RENDER HTML
        # =====================================================
        html = render(
            request,
            self.template_name,
            {
                "ads": ads
            }
        ).content.decode("utf-8")

        return JsonResponse({
            "success": True,
            "html": html
        })


import random

from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import View


@method_decorator(login_required, name="dispatch")
class ProblemSponsoredAdsView(View):

    template_name = "partials/smart-card-ads.module.html"
    now = timezone.now()
    def get(self, request, problem_id):

        problem = get_object_or_404(Problem, id=problem_id)
        now = timezone.now()

        # =========================
        # BASE QUERYSET
        # =========================
        base_ads = Advertisement.objects.filter(
            status="active",
            is_deleted=False
        ).filter(
            Q(start_at__isnull=True) | Q(start_at__lte=now)
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        )

        # =========================
        # PRIORITY ADS
        # =========================
        problem_ads = base_ads.filter(related_problem=problem)

        ads_qs = problem_ads if problem_ads.exists() else base_ads.filter(
            related_problem__isnull=True
        )

        ads = list(ads_qs)

        # =========================
        # NO ADS → CLEAN RESPONSE
        # =========================
        if not ads:
            return JsonResponse({
                "success": False,
                "html": "",
                "state": "no_ads_available"
            })

        # =========================
        # PICK RANDOM AD
        # =========================
        ad = random.choice(ads)

        # =========================
        # TRACK IMPRESSION
        # =========================
        Advertisement.objects.filter(pk=ad.pk).update(
            impressions=F("impressions") + 1
        )

        # =========================
        # SAFE RENDER
        # =========================
        try:
            html = render(
                request,
                self.template_name,
                {"ad": ad}
            ).content.decode("utf-8")

            html = html.strip() if html else ""

            if not html:
                return JsonResponse({
                    "success": False,
                    "html": "",
                    "state": "empty_render"
                })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "html": "",
                "state": "render_error"
            })

        # =========================
        # SUCCESS
        # =========================
        return JsonResponse({
            "success": True,
            "html": html,
            "ad_id": str(ad.id),
            "state": "ok"
        })
        
# ============================================================
# TRACK CLICK
# ============================================================
@method_decorator(login_required, name="dispatch")
class AdClickView(View):

    def get(self, request, ad_id):

        updated = Advertisement.objects.filter(id=ad_id).update(
            clicks=F("clicks") + 1
        )

        if not updated:
            return JsonResponse({"success": False, "error": "not_found"}, status=404)

        ad = Advertisement.objects.get(id=ad_id)

        return redirect(ad.target_url)
    
    
@method_decorator(login_required, name="dispatch")
class SaveAdDraftView(View):

    def post(self, request):

        title = request.POST.get("title")
        description = request.POST.get("description")
        url = request.POST.get("url")
        category = request.POST.get("ad_category")
        duration = request.POST.get("duration_days")
        ads_file = request.FILES.get("ads_file")

        if not title:
            return JsonResponse({"success": False, "error": "title_required"}, status=400)

        ad = Advertisement.objects.create(
            advertiser=request.user,
            advertiser_name=request.user.username,
            title=title,
            description=description,
            target_url=url,
            ad_category=category,
            duration_days=duration or 7,
            ads_file=ads_file,
            status="draft"
        )

        return JsonResponse({
            "success": True,
            "ad_id": str(ad.id),
            "message": "Draft saved successfully"
        })
        

# =========================================================
# EDIT DRAFT AD
# =========================================================
@method_decorator(login_required, name="dispatch")
class EditDraftAdView(View):

    template_name = "edit_ad.html"

    def get(self, request, ad_id):

        ad = get_object_or_404(
            Advertisement,
            id=ad_id,
            advertiser=request.user,
            status="draft",
            is_deleted=False
        )

        context = {
            "ad": ad
        }

        return render(
            request,
            self.template_name,
            context
        )

    def post(self, request, ad_id):

        ad = get_object_or_404(
            Advertisement,
            id=ad_id,
            advertiser=request.user,
            status="draft",
            is_deleted=False
        )

        ad.title = request.POST.get("title")
        ad.description = request.POST.get("description")
        ad.ad_category = request.POST.get("ad_category")
        ad.target_url = request.POST.get("target_url")
        ad.duration_days = request.POST.get("duration_days")

        if request.FILES.get("ads_file"):
            ad.ads_file = request.FILES.get("ads_file")

        ad.save()

        messages.success(
            request,
            "Draft updated successfully."
        )

        return redirect("ads_dashboard")


# =========================================================
# RELAUNCH / EXTEND AD
# =========================================================
from datetime import timedelta

@method_decorator(login_required, name="dispatch")
class RelaunchAdView(View):

    def post(self, request, ad_id):

        ad = get_object_or_404(
            Advertisement,
            id=ad_id,
            advertiser=request.user,
            is_deleted=False
        )

        now = timezone.now()

        # =============================================
        # IF AD IS ACTIVE → EXTEND FROM CURRENT EXPIRY
        # =============================================
        if ad.status == "active" and ad.expires_at:

            ad.expires_at += timedelta(
                days=ad.duration_days
            )

        # =============================================
        # OTHERWISE → START NEW CYCLE
        # =============================================
        else:

            ad.start_at = now

            ad.expires_at = now + timedelta(
                days=ad.duration_days
            )

            ad.status = "active"

        ad.relaunch_count += 1

        # If ad was manually relaunched, keep recurring enabled if you want:
        # (optional rule)
        # ad.is_recurring = True

        ad.save()

        messages.success(
            request,
            "Advertisement relaunched successfully."
        )

        return redirect("ads_dashboard")


# =========================================================
# ENABLE RECURRING
# =========================================================
@method_decorator(login_required, name="dispatch")
class EnableRecurringAdView(View):

    def post(self, request, ad_id):

        ad = get_object_or_404(
            Advertisement,
            id=ad_id,
            advertiser=request.user,
            is_deleted=False
        )

        recurring_days = int(
            request.POST.get("recurring_days", 7)
        )

        allowed_days = [3, 7, 14, 30]

        if recurring_days not in allowed_days:

            messages.error(
                request,
                "Invalid recurring duration."
            )
            return redirect("ads_dashboard")

        ad.is_recurring = True
        ad.stop_recurring = False
        ad.recurring_days = recurring_days

        # IMPORTANT: ensure it is active if expired
        if ad.expires_at and ad.expires_at < timezone.now():
            ad.expires_at = timezone.now() + timedelta(days=recurring_days)

        ad.status = "active"

        ad.save()

        messages.success(
            request,
            f"Recurring enabled every {recurring_days} days."
        )

        return redirect("ads_dashboard")


# =========================================================
# STOP RECURRING
# =========================================================
@method_decorator(login_required, name="dispatch")
class StopRecurringAdView(View):

    def post(self, request, ad_id):

        ad = get_object_or_404(
            Advertisement,
            id=ad_id,
            advertiser=request.user,
            is_deleted=False
        )

        ad.stop_recurring = True
        ad.is_recurring = False

        ad.save()

        messages.success(
            request,
            "Recurring subscription stopped."
        )

        return redirect("ads_dashboard")


# =========================================================
# DELETE AD
# =========================================================
@method_decorator(login_required, name="dispatch")
class DeleteAdView(View):

    def post(self, request, ad_id):

        ad = get_object_or_404(
            Advertisement,
            id=ad_id,
            advertiser=request.user
        )

        ad.is_deleted = True

        ad.deleted_at = timezone.now()

        ad.stop_recurring = True

        ad.is_recurring = False

        ad.save()

        messages.success(
            request,
            "Advertisement deleted successfully."
        )

        return redirect("ads_dashboard")