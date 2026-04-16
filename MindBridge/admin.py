from django.contrib import admin
from MindBridge.models import *

# =========================================================
# 🔹 USER ADMIN
# =========================================================

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "reputation_score", "is_verified_expert", "created_at")
    search_fields = ("username", "email")
    list_filter = ("is_verified_expert", "created_at")
    ordering = ("-created_at",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "country", "profession")
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


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "payment_type", "status", "created_at")
    list_filter = ("payment_type", "status")
    search_fields = ("user__username", "reference_id")


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

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ("advertiser_name", "status", "price", "start_at", "expires_at")
    list_filter = ("status",)
    search_fields = ("advertiser_name",)


@admin.register(ProblemPromotion)
class ProblemPromotionAdmin(admin.ModelAdmin):
    list_display = ("problem", "promotion_type", "expires_at")
    list_filter = ("promotion_type",)
    search_fields = ("problem__title",)


# =========================================================
# 🔹 CREATOR SUBSCRIPTIONS
# =========================================================

@admin.register(CreatorSubscription)
class CreatorSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("creator", "subscriber", "monthly_fee", "active")
    list_filter = ("active",)
    search_fields = ("creator__username", "subscriber__username")


# =========================================================
# 🔹 BOOKMARKS & ANALYTICS
# =========================================================

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "created_at")
    search_fields = ("user__username", "problem__title")


@admin.register(ProblemView)
class ProblemViewAdmin(admin.ModelAdmin):
    list_display = ("problem", "user", "ip_address", "viewed_at")
    search_fields = ("problem__title", "ip_address")
    ordering = ("-viewed_at",)


# =========================================================
# 🔹 EVENTS
# =========================================================

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "host", "is_public", "is_live", "start_time")
    list_filter = ("is_public", "is_live")
    search_fields = ("title", "host__username")


@admin.register(EventParticipant)
class EventParticipantAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "joined_at")


@admin.register(EventInvitation)
class EventInvitationAdmin(admin.ModelAdmin):
    list_display = ("event", "invited_user", "accepted")
    list_filter = ("accepted",)


@admin.register(EventRecording)
class EventRecordingAdmin(admin.ModelAdmin):
    list_display = ("event", "created_at")


# =========================================================
# 🔹 PAYPAL
# =========================================================

@admin.register(PayPalAccount)
class PayPalAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "paypal_email", "connected_at")
    search_fields = ("user__username", "paypal_email")


# =========================================================
# 🔹 KNOWLEDGE BASE (🔥 IMPORTANT)
# =========================================================

@admin.register(KnowledgeBaseEntry)
class KnowledgeBaseEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "problem", "created_at")
    search_fields = ("title", "description", "problem__title")
    list_filter = ("category",)
    ordering = ("-created_at",)


# =========================================================
# 🔹 REPUTATION LOG
# =========================================================

@admin.register(ReputationLog)
class ReputationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "reason", "created_at")
    search_fields = ("user__username", "reason")