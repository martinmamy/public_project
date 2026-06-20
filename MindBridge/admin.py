from django.contrib import admin
from MindBridge.models import *
from django.db.models import Sum, Count, F
from django.utils.html import format_html
from django.utils import timezone
# =========================================================
# 🔹 USER ADMIN
# =========================================================

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "avatar", "reputation_score", "is_verified_expert", "created_at")
    search_fields = ("username", "email")
    list_filter = ("is_verified_expert", "created_at")
    ordering = ("-created_at",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "country", "profession", "first_name", "last_name")
    search_fields = ("user__username", "country", "profession")
    list_filter = ("country", "profession")


# =========================================================
# 🔹 PROBLEM & ANSWER SYSTEM
# =========================================================

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "is_solved", "votes_score", "views_count", "created_at")
    search_fields = ("title", "description", "tags")
    list_filter = ("category", "is_solved", "created_at")
    ordering = ("-created_at",)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("problem", "author", "is_accepted", "votes_score", "created_at")
    search_fields = ("content", "author__username")
    list_filter = ("is_accepted", "created_at")
    ordering = ("-created_at",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "answer", "created_at")
    search_fields = ("content", "user__username")
    ordering = ("-created_at",)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "answer", "value", "created_at")
    list_filter = ("value",)


# =========================================================
# 🔹 SOCIAL
# =========================================================

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__username", "following__username")


# =========================================================
# 🔹 MONEY (TIPS / BOUNTY / PAYMENTS)
# =========================================================

@admin.register(Tip)
class TipAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "amount", "created_at")
    search_fields = ("sender__username", "receiver__username")


@admin.register(Bounty)
class BountyAdmin(admin.ModelAdmin):
    list_display = ("problem", "amount", "status", "expires_at")
    list_filter = ("status",)
    search_fields = ("problem__title",)


# =========================================================
# 🔹 NOTIFICATIONS & REPORTS
# =========================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("message",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("reporter", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reason",)


# =========================================================
# 🔹 ADS & PROMOTION
# =========================================================

# admin.py

from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from .models import Advertisement


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):

    # =====================================================
    # TABLE DISPLAY
    # =====================================================

    list_display = (
        "ad_preview",
        "advertiser_display",
        "status_badge",
        "category_display",
        "impressions_display",
        "clicks_display",
        "ctr_display",
        "revenue_display",
        "recurring_display",
        "campaign_dates",
        "created_display",
    )

    # =====================================================
    # FILTERS
    # =====================================================

    list_filter = (
        "status",
        "ad_category",
        "is_recurring",
        "created_at",
        "expires_at",
    )

    # =====================================================
    # SEARCH
    # =====================================================

    search_fields = (
        "title",
        "description",
        "advertiser__username",
        "advertiser_name",
    )

    # =====================================================
    # ORDERING
    # =====================================================

    ordering = ("-created_at",)

    # =====================================================
    # READ ONLY
    # =====================================================

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "impressions",
        "clicks",
        "relaunch_count",
        "next_relaunch_at",
    )

    # =====================================================
    # PAGINATION
    # =====================================================

    list_per_page = 25

    # =====================================================
    # FIELDSETS
    # =====================================================

    fieldsets = (

        ("Advertisement Info", {
            "fields": (
                "id",
                "advertiser",
                "advertiser_name",
                "title",
                "description",
                "ad_category",
                "ads_file",
                "target_url",
                "related_problem",
            )
        }),

        ("Billing", {
            "fields": (
                "price",
                "duration_days",
            )
        }),

        ("Campaign", {
            "fields": (
                "status",
                "start_at",
                "expires_at",
            )
        }),

        ("Analytics", {
            "fields": (
                "impressions",
                "clicks",
                "relaunch_count",
            )
        }),

        ("Recurring Ads", {
            "fields": (
                "is_recurring",
                "recurring_every",
                "next_relaunch_at",
                "stop_recurring",
            )
        }),

        ("Soft Delete", {
            "fields": (
                "is_deleted",
                "deleted_at",
            )
        }),

        ("Tracking", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),

    )

    # =====================================================
    # PREVIEW
    # =====================================================

    def ad_preview(self, obj):

        if obj.ads_file:
            return format_html(
                """
                <div style="
                    display:flex;
                    align-items:center;
                    gap:12px;
                ">

                    <img src="{}"
                         style="
                            width:60px;
                            height:60px;
                            border-radius:12px;
                            object-fit:cover;
                            border:1px solid #ddd;
                         ">

                    <div>

                        <div style="
                            font-weight:700;
                            font-size:14px;
                            margin-bottom:4px;
                        ">
                            {}
                        </div>

                        <div style="
                            color:#777;
                            font-size:12px;
                            max-width:220px;
                            overflow:hidden;
                            text-overflow:ellipsis;
                            white-space:nowrap;
                        ">
                            {}
                        </div>

                    </div>

                </div>
                """,
                obj.ads_file.url,
                obj.title,
                obj.description
            )

        return obj.title

    ad_preview.short_description = "Advertisement"

    # =====================================================
    # ADVERTISER
    # =====================================================

    def advertiser_display(self, obj):

        if obj.advertiser:
            return format_html(
                """
                <span style="
                    font-weight:600;
                    color:#0d6efd;
                ">
                    @{}
                </span>
                """,
                obj.advertiser.username
            )

        return obj.advertiser_name

    advertiser_display.short_description = "Advertiser"

    # =====================================================
    # STATUS BADGE
    # =====================================================

    def status_badge(self, obj):

        colors = {
            "active": "#198754",
            "pending": "#ffc107",
            "draft": "#6c757d",
            "expired": "#212529",
            "rejected": "#dc3545",
        }

        text_colors = {
            "pending": "#000",
        }

        bg = colors.get(obj.status, "#999")
        text = text_colors.get(obj.status, "#fff")

        return format_html(
            """
            <span style="
                background:{};
                color:{};
                padding:6px 12px;
                border-radius:20px;
                font-size:12px;
                font-weight:700;
                display:inline-block;
                min-width:75px;
                text-align:center;
            ">
                {}
            </span>
            """,
            bg,
            text,
            obj.status.upper()
        )

    status_badge.short_description = "Status"

    # =====================================================
    # CATEGORY
    # =====================================================

    def category_display(self, obj):

        return format_html(
            """
            <span style="
                font-weight:600;
                color:#444;
            ">
                {}
            </span>
            """,
            obj.ad_category
        )

    category_display.short_description = "Category"

    # =====================================================
    # IMPRESSIONS
    # =====================================================

    def impressions_display(self, obj):

        return format_html(
            """
            <span style="
                font-weight:700;
                color:#0d6efd;
            ">
                {}
            </span>
            """,
            f"{obj.impressions:,}"
        )

    impressions_display.short_description = "Impressions"

    # =====================================================
    # CLICKS
    # =====================================================

    def clicks_display(self, obj):

        return format_html(
            """
            <span style="
                font-weight:700;
                color:#6f42c1;
            ">
                {}
            </span>
            """,
            f"{obj.clicks:,}"
        )

    clicks_display.short_description = "Clicks"

    # =====================================================
    # CTR
    # =====================================================

    def ctr_display(self, obj):

        if obj.impressions > 0:
            ctr = round((obj.clicks / obj.impressions) * 100, 2)
        else:
            ctr = 0

        color = "#198754" if ctr >= 5 else "#fd7e14"

        return format_html(
            """
            <span style="
                color:{};
                font-weight:700;
                font-size:13px;
            ">
                {}%
            </span>
            """,
            color,
            ctr
        )

    ctr_display.short_description = "CTR"

    # =====================================================
    # REVENUE
    # =====================================================

    def revenue_display(self, obj):

        return format_html(
            """
            <span style="
                color:#198754;
                font-weight:700;
                font-size:14px;
            ">
                ${}
            </span>
            """,
            obj.price
        )

    revenue_display.short_description = "Revenue"

    # =====================================================
    # RECURRING
    # =====================================================

    def recurring_display(self, obj):

        if obj.is_recurring:

            return format_html(
                """
                <span style="
                    background:#fff3cd;
                    color:#856404;
                    padding:5px 10px;
                    border-radius:20px;
                    font-size:12px;
                    font-weight:700;
                ">
                    Every {} Days
                </span>
                """,
                obj.recurring_every
            )

        return format_html(
            """
            <span style="
                color:#999;
                font-size:12px;
            ">
                Not Recurring
            </span>
            """
        )

    recurring_display.short_description = "Recurring"

    # =====================================================
    # CAMPAIGN DATES
    # =====================================================

    def campaign_dates(self, obj):

        return format_html(
            """
            <div style="font-size:12px;line-height:1.6;">

                <div>
                    <strong>Start:</strong> {}
                </div>

                <div>
                    <strong>End:</strong> {}
                </div>

            </div>
            """,
            obj.start_at.strftime("%b %d, %Y") if obj.start_at else "-",
            obj.expires_at.strftime("%b %d, %Y") if obj.expires_at else "-"
        )

    campaign_dates.short_description = "Campaign"

    # =====================================================
    # CREATED
    # =====================================================

    def created_display(self, obj):

        return format_html(
            """
            <span style="
                font-weight:600;
                color:#555;
            ">
                {}
            </span>
            """,
            obj.created_at.strftime("%b %d, %Y")
        )

    created_display.short_description = "Created"

    # =====================================================
    # DASHBOARD SUMMARY
    # =====================================================

    def changelist_view(self, request, extra_context=None):

        extra_context = extra_context or {}

        queryset = Advertisement.objects.filter(is_deleted=False)

        # COUNTS
        total_ads = queryset.count()
        active_ads = queryset.filter(status="active").count()
        pending_ads = queryset.filter(status="pending").count()
        expired_ads = queryset.filter(status="expired").count()
        draft_ads = queryset.filter(status="draft").count()
        rejected_ads = queryset.filter(status="rejected").count()

        # TOTALS
        total_revenue = queryset.aggregate(
            total=Sum("price")
        )["total"] or 0

        total_clicks = queryset.aggregate(
            total=Sum("clicks")
        )["total"] or 0

        total_impressions = queryset.aggregate(
            total=Sum("impressions")
        )["total"] or 0

        # GLOBAL CTR
        if total_impressions > 0:
            global_ctr = round(
                (total_clicks / total_impressions) * 100,
                2
            )
        else:
            global_ctr = 0

        # EXTRA CONTEXT
        extra_context.update({

            "ads_total": total_ads,

            "ads_active": active_ads,

            "ads_pending": pending_ads,

            "ads_expired": expired_ads,

            "ads_draft": draft_ads,

            "ads_rejected": rejected_ads,

            "ads_revenue": total_revenue,

            "ads_clicks": total_clicks,

            "ads_impressions": total_impressions,

            "ads_ctr": global_ctr,

        })

        return super().changelist_view(
            request,
            extra_context=extra_context
        )


@admin.register(ProblemPromotion)
class ProblemPromotionAdmin(admin.ModelAdmin):
    list_display = ("problem", "promotion_type", "expires_at")
    list_filter = ("promotion_type",)
    search_fields = ("problem__title",)


# =========================================================
# 🔹 CREATOR SUBSCRIPTIONS
# =========================================================

@admin.register(CreatorsSubscription)
class CreatorsSubscriptionAdmin(admin.ModelAdmin):

    # =====================================================
    # LIST DISPLAY
    # =====================================================

    list_display = (
        "user",
        "plan",
        "amount",
        "currency",
        "status",
        "active",
        "premium_access",
        "started_at",
        "next_billing_time",
        "created_at",
    )

    # =====================================================
    # FILTERS
    # =====================================================

    list_filter = (
        "status",
        "plan",
        "active",
        "premium_access",
        "created_at",
        "started_at",
    )

    # =====================================================
    # SEARCH
    # =====================================================

    search_fields = (
        "user__email",
        "paypal_subscription_id",
        "paypal_plan_id",
        "uuid",
    )

    # =====================================================
    # READONLY FIELDS
    # =====================================================

    readonly_fields = (
        "uuid",
        "paypal_subscription_id",
        "paypal_plan_id",
        "created_at",
        "updated_at",
        "started_at",
        "cancelled_at",
        "expired_at",
    )

    # =====================================================
    # ORDERING
    # =====================================================

    ordering = (
        "-created_at",
    )

    # =====================================================
    # FIELDSETS
    # =====================================================

    fieldsets = (

        (
            "Subscription Information",
            {
                "fields": (
                    "uuid",
                    "user",
                    "plan",
                    "amount",
                    "currency",
                )
            }
        ),

        (
            "PayPal Information",
            {
                "fields": (
                    "paypal_subscription_id",
                    "paypal_plan_id",
                )
            }
        ),

        (
            "Subscription Status",
            {
                "fields": (
                    "status",
                    "active",
                    "premium_access",
                )
            }
        ),

        (
            "Billing Dates",
            {
                "fields": (
                    "started_at",
                    "next_billing_time",
                    "cancelled_at",
                    "expired_at",
                )
            }
        ),

        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            }
        ),
    )

    # =====================================================
    # PAGINATION
    # =====================================================

    list_per_page = 25

    # =====================================================
    # QUICK BOOLEAN EDITS
    # =====================================================

    list_editable = (
        "status",
        "active",
        "premium_access",
    )

    # =====================================================
    # OPTIMIZATION
    # =====================================================

    autocomplete_fields = (
        "user",
    )


# =========================================================
# 🔹 REPUTATION LOG
# =========================================================

@admin.register(ReputationLog)
class ReputationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "reason", "created_at")
    search_fields = ("user__username", "reason")
    
from django.contrib import admin

from .models import (


    EventHub,
    EventReminder,
    LiveSession,
)
from django.utils.html import format_html

# =========================================================
# BOOKMARK ADMIN
# =========================================================
@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "problem",
        "created_at",
    )

    search_fields = (
        "user__username",
        "problem__title",
    )

    list_filter = (
        "created_at",
    )

    autocomplete_fields = (
        "user",
        "problem",
    )

    ordering = ("-created_at",)


# =========================================================
# PROBLEM VIEW ANALYTICS ADMIN
# =========================================================
@admin.register(ProblemView)
class ProblemViewAdmin(admin.ModelAdmin):

    list_display = (
        "problem",
        "user",
        "ip_address",
        "viewed_at",
    )

    search_fields = (
        "problem__title",
        "user__username",
        "ip_address",
    )

    list_filter = (
        "viewed_at",
    )

    autocomplete_fields = (
        "problem",
        "user",
    )

    ordering = ("-viewed_at",)


# =========================================================
# PAYMENT ADMIN
# =========================================================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "amount",
        "payment_type",
        "status",
        "reference_id",
        "created_at",
    )

    search_fields = (
        "user__username",
        "reference_id",
    )

    list_filter = (
        "payment_type",
        "status",
        "created_at",
    )

    autocomplete_fields = (
        "user",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
    )


# =========================================================
# EVENT HUB ADMIN
# =========================================================
@admin.register(EventHub)
class EventHubAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "host",
        "category",
        "start_time",
        "end_time",
        "created_at",
    )

    search_fields = (
        "title",
        "host__username",
        "category",
    )

    list_filter = (
        "category",
        "created_at",
        "start_time",
    )

    autocomplete_fields = (
        "host",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "id",
        "created_at",
    )


# =========================================================
# EVENT REMINDER ADMIN
# =========================================================
@admin.register(EventReminder)
class EventReminderAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "event",
        "remind_at",
        "sent",
        "created_at",
    )

    search_fields = (
        "user__username",
        "event__title",
    )

    list_filter = (
        "sent",
        "remind_at",
        "created_at",
    )

    autocomplete_fields = (
        "user",
        "event",
    )

    ordering = ("-created_at",)


# =========================================================
# EVENT ADMIN
# =========================================================
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "host",
        "is_public",
        "is_live",
        "start_time",
        "end_time",
        "created_at",
    )

    search_fields = (
        "title",
        "host__username",
    )

    list_filter = (
        "is_public",
        "is_live",
        "created_at",
    )

    autocomplete_fields = (
        "host",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "id",
        "created_at",
    )


# =========================================================
# EVENT PARTICIPANT ADMIN
# =========================================================
@admin.register(EventParticipant)
class EventParticipantAdmin(admin.ModelAdmin):

    list_display = (
        "event",
        "user",
        "joined_at",
    )

    search_fields = (
        "event__title",
        "user__username",
    )

    list_filter = (
        "joined_at",
    )

    autocomplete_fields = (
        "event",
        "user",
    )

    ordering = ("-joined_at",)


# =========================================================
# EVENT INVITATION ADMIN
# =========================================================
@admin.register(EventInvitation)
class EventInvitationAdmin(admin.ModelAdmin):

    list_display = (
        "event",
        "invited_user",
        "invited_by",
        "accepted",
        "created_at",
    )

    search_fields = (
        "event__title",
        "invited_user__username",
        "invited_by__username",
    )

    list_filter = (
        "accepted",
        "created_at",
    )

    autocomplete_fields = (
        "event",
        "invited_user",
        "invited_by",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

    ordering = ("-created_at",)


# =========================================================
# EVENT RECORDING ADMIN
# =========================================================
@admin.register(EventRecording)
class EventRecordingAdmin(admin.ModelAdmin):

    list_display = (
        "event",
        "file",
        "created_at",
    )

    search_fields = (
        "event__title",
    )

    list_filter = (
        "created_at",
    )

    autocomplete_fields = (
        "event",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

    ordering = ("-created_at",)


# =========================================================
# PAYPAL ACCOUNT ADMIN
# =========================================================
@admin.register(PayPalAccount)
class PayPalAccountAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "paypal_email",
        "payer_id",
        "connected_at",
    )

    search_fields = (
        "user__username",
        "paypal_email",
        "payer_id",
    )

    autocomplete_fields = (
        "user",
    )

    readonly_fields = (
        "id",
        "connected_at",
    )

    ordering = ("-connected_at",)


# =========================================================
# KNOWLEDGE BASE ADMIN
# =========================================================
@admin.register(KnowledgeBaseEntry)
class KnowledgeBaseEntryAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "category",
        "problem",
        "answer",
        "created_at",
    )

    search_fields = (
        "title",
        "category",
        "problem__title",
    )

    list_filter = (
        "category",
        "created_at",
    )

    autocomplete_fields = (
        "problem",
        "answer",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

    ordering = ("-created_at",)


# =========================================================
# LIVE SESSION ADMIN
# =========================================================
@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):

    list_display = (
        "expert",
        "client",
        "provider",
        "duration",
        "status",
        "created_at",
        "ended_at",
    )

    search_fields = (
        "expert__username",
        "client__username",
    )

    list_filter = (
        "provider",
        "status",
        "created_at",
    )

    autocomplete_fields = (
        "expert",
        "client",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

    ordering = ("-created_at",)
    

from django.contrib import admin

from .models import (
    AvailabilitySlot,
    Booking,
    Review,
    SendEmail,
    UserReport,
)


# =========================================================
# AVAILABILITY SLOT ADMIN
# =========================================================
@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):

    list_display = (
        "expert",
        "start_time",
        "end_time",
        "price",
        "currency",
        "unit",
        "is_booked",
        "is_archived",
        "created_at",
    )

    search_fields = (
        "expert__username",
        "description",
    )

    list_filter = (
        "unit",
        "currency",
        "is_booked",
        "is_archived",
        "created_at",
    )

    autocomplete_fields = (
        "expert",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (
            "Expert Information",
            {
                "fields": (
                    "expert",
                )
            }
        ),

        (
            "Schedule",
            {
                "fields": (
                    "start_time",
                    "end_time",
                )
            }
        ),

        (
            "Pricing",
            {
                "fields": (
                    "price",
                    "currency",
                    "unit",
                )
            }
        ),

        (
            "Details",
            {
                "fields": (
                    "description",
                    "is_booked",
                    "is_archived",
                )
            }
        ),

        (
            "System",
            {
                "fields": (
                    "id",
                    "created_at",
                )
            }
        ),
    )


# =========================================================
# BOOKING ADMIN
# =========================================================
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):

    list_display = (
        "slot",
        "booked_by",
        "meeting_link",
        "is_cancelled",
        "created_at",
        "cancelled_at",
    )

    search_fields = (
        "booked_by__username",
        "slot__expert__username",
        "meeting_link",
    )

    list_filter = (
        "is_cancelled",
        "created_at",
        "cancelled_at",
    )

    autocomplete_fields = (
        "slot",
        "booked_by",
    )

    readonly_fields = (
        "id",
        "meeting_link",
        "created_at",
        "cancelled_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (
            "Booking Information",
            {
                "fields": (
                    "slot",
                    "booked_by",
                    "details",
                )
            }
        ),

        (
            "Meeting",
            {
                "fields": (
                    "meeting_link",
                )
            }
        ),

        (
            "Status",
            {
                "fields": (
                    "is_cancelled",
                    "cancelled_at",
                )
            }
        ),

        (
            "System",
            {
                "fields": (
                    "id",
                    "created_at",
                )
            }
        ),
    )


# =========================================================
# REVIEW ADMIN
# =========================================================
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):

    list_display = (
        "reviewer",
        "reviewed_user",
        "rating",
        "created_at",
    )

    search_fields = (
        "reviewer__username",
        "reviewed_user__username",
        "comment",
    )

    list_filter = (
        "rating",
        "created_at",
    )

    autocomplete_fields = (
        "booking",
        "reviewer",
        "reviewed_user",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (
            "Review Information",
            {
                "fields": (
                    "booking",
                    "reviewer",
                    "reviewed_user",
                    "rating",
                    "comment",
                )
            }
        ),

        (
            "System",
            {
                "fields": (
                    "created_at",
                )
            }
        ),
    )


# =========================================================
# SEND EMAIL ADMIN
# =========================================================
@admin.register(SendEmail)
class SendEmailAdmin(admin.ModelAdmin):

    list_display = (
        "subject",
        "recipient",
        "admin_user",
        "sent_at",
    )

    search_fields = (
        "subject",
        "recipient",
        "admin_user__username",
    )

    list_filter = (
        "sent_at",
    )

    autocomplete_fields = (
        "admin_user",
    )

    readonly_fields = (
        "id",
        "sent_at",
    )

    ordering = ("-sent_at",)

    fieldsets = (
        (
            "Email Information",
            {
                "fields": (
                    "admin_user",
                    "recipient",
                    "subject",
                    "body",
                )
            }
        ),

        (
            "System",
            {
                "fields": (
                    "id",
                    "sent_at",
                )
            }
        ),
    )


# =========================================================
# USER REPORT ADMIN
# =========================================================
@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):

    list_display = (
        "reporter",
        "reported_user",
        "created_at",
        "has_evidence",
    )

    search_fields = (
        "reporter__username",
        "reported_user__username",
        "reason",
    )

    list_filter = (
        "created_at",
    )

    autocomplete_fields = (
        "reporter",
        "reported_user",
    )

    readonly_fields = (
        "created_at",
        "evidence_preview",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (
            "Report Information",
            {
                "fields": (
                    "reporter",
                    "reported_user",
                    "reason",
                )
            }
        ),

        (
            "Evidence",
            {
                "fields": (
                    "evidence_ads_file",
                    "evidence_preview",
                )
            }
        ),

        (
            "System",
            {
                "fields": (
                    "created_at",
                )
            }
        ),
    )

    # =====================================================
    # EVIDENCE STATUS
    # =====================================================
    @admin.display(boolean=True, description="Evidence")
    def has_evidence(self, obj):

        return bool(obj.evidence_ads_file)

    # =====================================================
    # IMAGE PREVIEW
    # =====================================================
    @admin.display(description="Evidence Preview")
    def evidence_preview(self, obj):

        if obj.evidence_ads_file:

            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" '
                'style="max-height:220px; border-radius:10px;" />'
                '</a>',
                obj.evidence_ads_file.url,
                obj.evidence_ads_file.url
            )

        return "No evidence uploaded"


from MindBridge.models import PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):

    # =====================================================
    # LIST DISPLAY
    # =====================================================
    list_display = (

        "id",

        "user",

        "browser",

        "short_endpoint",

        "created_at"
    )

    # =====================================================
    # SEARCH
    # =====================================================
    search_fields = (

        "user__username",

        "browser",

        "endpoint"
    )

    # =====================================================
    # FILTERS
    # =====================================================
    list_filter = (

        "browser",

        "created_at"
    )

    # =====================================================
    # ORDERING
    # =====================================================
    ordering = (

        "-created_at",
    )

    # =====================================================
    # READONLY FIELDS
    # =====================================================
    readonly_fields = (

        "created_at",
    )

    # =====================================================
    # FIELDSETS
    # =====================================================
    fieldsets = (

        (
            "User Info",
            {

                "fields": (
                    "user",
                    "browser"
                )
            }
        ),

        (
            "Push Subscription",
            {

                "fields": (

                    "endpoint",

                    "p256dh",

                    "auth"
                )
            }
        ),

        (
            "Metadata",
            {

                "fields": (
                    "created_at",
                )
            }
        )
    )

    # =====================================================
    # PAGINATION
    # =====================================================
    list_per_page = 25

    # =====================================================
    # SHORT ENDPOINT DISPLAY
    # =====================================================
    def short_endpoint(self, obj):

        if not obj.endpoint:
            return "-"

        return f"{obj.endpoint[:70]}..."

    short_endpoint.short_description = "Endpoint"