import datetime
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db.models import Q, F
from MindBridge.predefined import PREDEFINED_CATEGORIES
from django.utils import timezone
from datetime import timedelta
from urllib.parse import urlparse
from MindBridge.validators import validate_safe_meeting_url  # if you placed it separately
from django.db import models
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError


from django.core.exceptions import ValidationError

import os

def validate_file_size(value):
    ext = os.path.splitext(value.name)[1].lower()

    # Define limits (in MB)
    IMAGE_MAX_MB = 5
    VIDEO_MAX_MB = 50
    AUDIO_MAX_MB = 10
    DEFAULT_MAX_MB = 20  # fallback

    image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    video_exts = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    audio_exts = ['.mp3', '.wav', '.ogg', '.aac']

    if ext in image_exts:
        max_size = IMAGE_MAX_MB
    elif ext in video_exts:
        max_size = VIDEO_MAX_MB
    elif ext in audio_exts:
        max_size = AUDIO_MAX_MB
    else:
        max_size = DEFAULT_MAX_MB  # fallback for unknown types

    if value.size > max_size * 1024 * 1024:
        raise ValidationError(
            f"File too large. Max size for this file type is {max_size}MB."
        )
        
        
def validate_ad_file_size(value):

    ext = os.path.splitext(value.name)[1].lower()

    # =====================================================
    # ADS-SPECIFIC LIMITS (STRICTER FOR PERFORMANCE)
    # =====================================================

    IMAGE_MAX_MB = 3      # ads must load fast
    VIDEO_MAX_MB = 25     # compressed ads recommended
    AUDIO_MAX_MB = 5
    DEFAULT_MAX_MB = 10   # unknown formats heavily restricted

    # =====================================================
    # FILE TYPE GROUPS
    # =====================================================

    image_exts = {'.jpg', '.jpeg', '.png', '.webp'}
    #video_exts = {'.mp4', '.webm'}

    # =====================================================
    # DETERMINE LIMIT
    # =====================================================

    if ext in image_exts:
        max_size = IMAGE_MAX_MB

    else:
        max_size = DEFAULT_MAX_MB

    # =====================================================
    # VALIDATION CHECK
    # =====================================================

    max_bytes = max_size * 1024 * 1024

    if value.size > max_bytes:
        raise ValidationError(
            f"Ad file too large ({ext or 'unknown type'}). "
            f"Max allowed size: {max_size}MB for ads."
        )
        

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    username = models.CharField(max_length=150, unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)

    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, validators=[validate_file_size])
    bio = models.TextField(blank=True)

    reputation_score = models.IntegerField(default=0, db_index=True)
    is_verified_expert = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["reputation_score"]),
            models.Index(fields=["created_at"]),
        ]

# =========================================================
# 2. USER PROFILE
# =========================================================

class UserProfile(models.Model):

    STATUS_CHOICES = [
        ("online", "Available now"),
        ("later", "Available later"),
        ("offline", "Offline"),
    ]

    REASON_CHOICES = [
        ("fix_bug", "Fix bug"),
        ("consultation", "Consultation"),
        ("session", "Live session"),
        ("other", "Other"),
    ]
    
    MODE_CHOICES = [
        ("onsite", "Onsite"),
        ("remote", "Remote"),
        ("not determined", "Not determined"),
    ]
    

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    country = models.CharField(max_length=100, db_index=True)
    profession = models.CharField(max_length=150, db_index=True)

    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)

    # 👇 NEW FIELDS
    availability_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="offline",
        db_index=True
    )
    availability_mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default="remote",
        db_index=True
    )

    availability_reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        blank=True,
        null=True
    )
    
    is_verification_recurring = models.BooleanField(default=False)

    verification_subscription_id = models.CharField(max_length=255, blank=True)
    verification_started_at = models.DateTimeField(null=True, blank=True)
    verified_until = models.DateTimeField(null=True, blank=True, db_index=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["country"]),
            models.Index(fields=["profession"]),
            models.Index(fields=["availability_status"]),
            models.Index(fields=["availability_mode"]),
        ]



class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=128)  # hashed
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=timezone.now() + timedelta(minutes=5))

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_expired()
    
# =========================================================
# 5. PROBLEM (MAIN POST)
# =========================================================

class Problem(models.Model):
    POST_TYPE_CHOICES = [
        ("issue", "Report an Issue"),
        ("information", "Share an Idea"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="problems")
    post_type = models.CharField(
        max_length=20,
        choices=POST_TYPE_CHOICES,
        default="issue",
        help_text="Select whether this post is an issue or information"
    )

    file = models.FileField(
        upload_to="problem_media/",
        blank=True,
        null=True,
        validators=[validate_file_size]
    )

    title = models.CharField(max_length=500)
    description = models.TextField()
    category = models.CharField(max_length=100, choices=PREDEFINED_CATEGORIES)

    # Comma-separated tags (no separate model)
    tags = models.CharField(max_length=250, blank=True, help_text="Comma-separated tags for this problem")

    is_solved = models.BooleanField(default=False, db_index=True)
    views_count = models.PositiveIntegerField(default=0)
    answers_count = models.PositiveIntegerField(default=0)
    votes_score = models.IntegerField(default=0)

    bounty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    tips_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    is_flagged = models.BooleanField(default=False)
    moderation_note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["votes_score"]),
            models.Index(fields=["views_count"]),
            models.Index(fields=["is_solved"]),
        ]

    def get_tags_list(self):
        """Return tags as a Python list"""
        return [t.strip() for t in self.tags.split(",") if t.strip()]


# =========================================================
# 7. ANSWERS
# =========================================================

class Answer(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    
    # Media is optional
    file = models.FileField(
        upload_to="problem_media/",
        blank=True,
        null=True,
        validators=[validate_file_size]
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="answers"
    )

    content = models.TextField()

    is_accepted = models.BooleanField(default=False, db_index=True)

    votes_score = models.IntegerField(default=0)

    tips_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    is_flagged = models.BooleanField(default=False)
    moderation_note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["votes_score"]),
            models.Index(fields=["created_at"]),
        ]


# =========================================================
# 8. COMMENTS
# =========================================================

class Comment(models.Model):
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")

    problem = models.ForeignKey(
        Problem,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    answer = models.ForeignKey(
        Answer,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    content = models.TextField()
    is_flagged = models.BooleanField(default=False)
    moderation_note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(problem__isnull=False) | Q(answer__isnull=False)
                ),
                name="comment_target_required"
            )
        ]


# =========================================================
# 9. VOTES
# =========================================================

class Vote(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    problem = models.ForeignKey(Problem, null=True, blank=True, on_delete=models.CASCADE)
    answer = models.ForeignKey(Answer, null=True, blank=True, on_delete=models.CASCADE)

    value = models.SmallIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [

            models.CheckConstraint(
                check=Q(value__in=[1, -1]),
                name="vote_value_valid"
            ),

            models.UniqueConstraint(
                fields=["user", "problem"],
                name="unique_problem_vote"
            ),

            models.UniqueConstraint(
                fields=["user", "answer"],
                name="unique_answer_vote"
            ),
        ]


# =========================================================
# 10. FOLLOW SYSTEM
# =========================================================

class Follow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follower = models.ForeignKey(
        User,
        related_name="following",
        on_delete=models.CASCADE
    )

    following = models.ForeignKey(
        User,
        related_name="followers",
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [

            models.UniqueConstraint(
                fields=["follower", "following"],
                name="unique_follow"
            ),

            models.CheckConstraint(
                check=~Q(follower=F("following")),
                name="prevent_self_follow"
            )
        ]


# =========================================================
# 11. TIPS
# =========================================================

class Tip(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name="tips", on_delete=models.CASCADE)

    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, blank=True, null=True)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, blank=True, null=True)

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1)]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["receiver"]),
        ]

# =========================================================
# 12. BOUNTY
# =========================================================

class Bounty(models.Model):
    
    STATUS = (
        ("held", "Held"),
        ("awarded", "Awarded"),
        ("refunded", "Refunded"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="held"
    )

    paypal_order_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    problem = models.OneToOneField(
        Problem,
        on_delete=models.CASCADE,
        related_name="bounty"
    )

    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_bounties"  # reverse accessor for bounties this user created
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    expires_at = models.DateTimeField()

    awarded_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="received_bounties"  # reverse accessor for bounties this user was awarded
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bounty for: {self.problem.title} | Amount: {self.amount}"


# =========================================================
# 13. CREATOR SUBSCRIPTIONS
# =========================================================


class CreatorsSubscription(models.Model):

    # =====================================================
    # SUBSCRIPTION STATUS
    # =====================================================

    class Status(models.TextChoices):

        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    # =====================================================
    # SUBSCRIPTION PLAN TYPES
    # =====================================================

    class Plan(models.TextChoices):

        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"

    # =====================================================
    # PRIMARY IDENTIFIER
    # =====================================================

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    # =====================================================
    # SUBSCRIBED USER
    # =====================================================

    user = models.ForeignKey(
        User,
        related_name="premium_subscriptions",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    # =====================================================
    # PAYPAL SUBSCRIPTION DATA
    # =====================================================

    paypal_subscription_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        null=True,
        blank=True
    )

    paypal_plan_id = models.CharField(
        max_length=255,
        default=""
    )

    # =====================================================
    # SUBSCRIPTION PLAN
    # =====================================================

    plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        default=Plan.MONTHLY
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    currency = models.CharField(
        max_length=10,
        default="USD"
    )

    # =====================================================
    # SUBSCRIPTION STATE
    # =====================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    active = models.BooleanField(
        default=False
    )

    # =====================================================
    # FEATURE ACCESS
    # =====================================================

    premium_access = models.BooleanField(
        default=False
    )

    # =====================================================
    # BILLING DATES
    # =====================================================

    started_at = models.DateTimeField(
        blank=True,
        null=True
    )

    next_billing_time = models.DateTimeField(
        blank=True,
        null=True
    )

    cancelled_at = models.DateTimeField(
        blank=True,
        null=True
    )

    expired_at = models.DateTimeField(
        blank=True,
        null=True
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =====================================================
    # MODEL CONFIGURATION
    # =====================================================

    class Meta:

        ordering = ["-created_at"]

        verbose_name = "Premium Subscription"

        verbose_name_plural = "Premium Subscriptions"

        constraints = [

            # ONLY ONE ACTIVE SUBSCRIPTION PER USER

            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(active=True),
                name="unique_active_subscription_per_user"
            )
        ]

        indexes = [

            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["paypal_subscription_id"]),
        ]

    # =====================================================
    # STRING REPRESENTATION
    # =====================================================

    def __str__(self):

        return (
            f"{self.user.email} | "
            f"{self.plan} | "
            f"{self.status}"
        )

    # =====================================================
    # ACTIVATE SUBSCRIPTION
    # =====================================================

    def activate(self):

        self.status = self.Status.ACTIVE

        self.active = True

        self.premium_access = True

        if not self.started_at:

            self.started_at = timezone.now()

        self.save(update_fields=[
            "status",
            "active",
            "premium_access",
            "started_at",
            "updated_at",
        ])

        # ENABLE USER PREMIUM FEATURES

        self.user.is_premium = True

        self.user.save(update_fields=[
            "is_premium"
        ])

    # =====================================================
    # CANCEL SUBSCRIPTION
    # =====================================================

    def cancel(self):

        self.status = self.Status.CANCELLED

        self.active = False

        self.premium_access = False

        self.cancelled_at = timezone.now()

        self.save(update_fields=[
            "status",
            "active",
            "premium_access",
            "cancelled_at",
            "updated_at",
        ])

        # REMOVE USER PREMIUM FEATURES

        self.user.is_premium = False

        self.user.save(update_fields=[
            "is_premium"
        ])

    # =====================================================
    # SUSPEND SUBSCRIPTION
    # =====================================================

    def suspend(self):

        self.status = self.Status.SUSPENDED

        self.active = False

        self.premium_access = False

        self.save(update_fields=[
            "status",
            "active",
            "premium_access",
            "updated_at",
        ])

        self.user.is_premium = False

        self.user.save(update_fields=[
            "is_premium"
        ])

    # =====================================================
    # EXPIRE SUBSCRIPTION
    # =====================================================

    def expire(self):

        self.status = self.Status.EXPIRED

        self.active = False

        self.premium_access = False

        self.expired_at = timezone.now()

        self.save(update_fields=[
            "status",
            "active",
            "premium_access",
            "expired_at",
            "updated_at",
        ])

        self.user.is_premium = False

        self.user.save(update_fields=[
            "is_premium"
        ])

    # =====================================================
    # CHECK ACCESS
    # =====================================================

    @property
    def has_access(self):

        return (
            self.active and
            self.premium_access and
            self.status == self.Status.ACTIVE
        )


# =========================================================
# 14. NOTIFICATIONS
# =========================================================

class Notification(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    
    actor = models.ForeignKey(
    User,
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="notifications_sent"
    )

    message = models.TextField()

    url = models.URLField(blank=True)

    is_read = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)



class PushSubscription(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="push_subscriptions"
    )

    endpoint = models.TextField()

    p256dh = models.TextField()

    auth = models.TextField()

    browser = models.CharField(
        max_length=255,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.browser}"

# =========================================================
# 15. REPORT SYSTEM
# =========================================================

class Report(models.Model):

    reporter = models.ForeignKey(User, on_delete=models.CASCADE)

    problem = models.ForeignKey(Problem, null=True, blank=True, on_delete=models.CASCADE)
    answer = models.ForeignKey(Answer, null=True, blank=True, on_delete=models.CASCADE)

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("reviewed", "Reviewed"),
            ("resolved", "Resolved")
        ],
        default="pending",
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)


# =========================================================
# 16. ADS
# =========================================================


# models.py
class Advertisement(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("active", "Active"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
    ]

    RECURRING_CHOICES = [
        (3, "Every 3 Days"),
        (7, "Every 7 Days"),
        (14, "Every 14 Days"),
        (30, "Every 30 Days"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    advertiser = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ads"
    )

    advertiser_name = models.CharField(max_length=200)

    title = models.CharField(
        max_length=255,
        db_index=True,
        default="Ad Title"
    )

    description = models.TextField(
        db_index=True,
        default="Ad Description"
    )

    ad_category = models.CharField(
        max_length=100,
        choices=PREDEFINED_CATEGORIES,
        db_index=True,
        default="Technology"
    )

    ads_file = models.FileField(
        upload_to="promos/",
        validators=[validate_ad_file_size]
    )

    target_url = models.URLField()

    related_problem = models.ForeignKey(
        "MindBridge.Problem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ads"
    )

    # =========================================
    # BILLING
    # =========================================
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    duration_days = models.PositiveIntegerField(default=7)

    # =========================================
    # CAMPAIGN DATES
    # =========================================
    start_at = models.DateTimeField(null=True, blank=True)

    expires_at = models.DateTimeField(null=True, blank=True)

    # =========================================
    # ANALYTICS
    # =========================================
    impressions = models.PositiveIntegerField(default=0)

    clicks = models.PositiveIntegerField(default=0)

    # =========================================
    # STATUS
    # =========================================
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="draft"
    )

    # =========================================
    # RECURRING ADS
    # =========================================
    is_recurring = models.BooleanField(default=False)

    recurring_every = models.PositiveIntegerField(
        choices=RECURRING_CHOICES,
        null=True,
        blank=True
    )

    next_relaunch_at = models.DateTimeField(
        null=True,
        blank=True
    )

    stop_recurring = models.BooleanField(default=False)

    # =========================================
    # SOFT DELETE
    # =========================================
    is_deleted = models.BooleanField(default=False)

    deleted_at = models.DateTimeField(
        null=True,
        blank=True
    )
    is_expiring_soon = models.BooleanField(default=False)
    is_urgent_expiry = models.BooleanField(default=False)

    # =========================================
    # TRACKING
    # =========================================
    relaunch_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title



class ProblemPromotion(models.Model):

    PROMOTION_TYPES = [
        ("featured", "Featured 24h"),
        ("boosted", "Boosted 3 Days"),
        ("pinned", "Pinned Homepage"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    problem = models.ForeignKey("Problem", on_delete=models.CASCADE, related_name="promotions")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPES)

    price = models.DecimalField(max_digits=8, decimal_places=2)

    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    paypal_order_id = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_active(self):
        return timezone.now() < self.expires_at
    
    
# =========================================================
# 17. REPUTATION LOG
# =========================================================

class ReputationLog(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    points = models.IntegerField()
    
    action = models.CharField(max_length=50, blank=True, null=True)
    
    reason = models.CharField(max_length=200)

    created_at = models.DateTimeField(auto_now_add=True)


# =========================================================
# 18. BOOKMARK
# =========================================================

class Bookmark(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "problem"],
                name="unique_bookmark"
            )
        ]


# =========================================================
# 19. PROBLEM VIEW ANALYTICS
# =========================================================

class ProblemView(models.Model):

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    ip_address = models.GenericIPAddressField(db_index=True)

    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["problem", "viewed_at"]),
        ]


# =========================================================
# 20. PAYMENTS
# =========================================================

class Payment(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.5)]
    )

    payment_type = models.CharField(
        max_length=50,
        choices=[
            ("tip", "Tip"),
            ("bounty", "Bounty"),
            ("subscription", "Subscription"),
            ("ad", "Advertisement"),
            ("booking", "Booking"),
        ],
        db_index=True
    )

    reference_id = models.CharField(max_length=200, unique=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("held", "Held"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
            
        ],
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
        

class EventHub(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    host = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="external_events"
    )
    category = models.CharField(max_length=100, choices=PREDEFINED_CATEGORIES, default="Technology")

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    meeting_url = models.URLField(blank=True, validators=[validate_safe_meeting_url])
    
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_upcoming(self):
        return self.start_time > timezone.now()

    @property
    def is_ongoing(self):
        now = timezone.now()
        return self.start_time <= now and (self.end_time is None or self.end_time >= now)

    @property
    def is_ended(self):
        return self.end_time is not None and self.end_time < timezone.now()

    def __str__(self):
        return self.title


# models.py
class EventReminder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(EventHub, on_delete=models.CASCADE)
    remind_at = models.DateTimeField()
    sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    

class Event(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    host = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="hosted_events"
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    is_public = models.BooleanField(default=True)
    
    # 🔴 THIS FIELD CONTROLS LIVE STATUS
    is_live = models.BooleanField(default=False)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # optional webinar link
    meeting_url = models.URLField(blank=True)

    def __str__(self):
        return self.title


class EventParticipant(models.Model):

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="participants"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["event", "user"]


class EventInvitation(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="invitations"
    )

    invited_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_event_invites"
    )

    accepted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["event", "invited_user"]
        
        
class EventRecording(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="recordings")
    file = models.FileField(upload_to="live_recordings/", validators=[validate_file_size])
    created_at = models.DateTimeField(auto_now_add=True)
    
    

class PayPalAccount(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="paypal_account"
    )

    paypal_email = models.EmailField()
    payer_id = models.CharField(max_length=255)

    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)

    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.paypal_email}"
    
    
class KnowledgeBaseEntry(models.Model):
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    problem = models.OneToOneField(
        Problem,
        on_delete=models.CASCADE,
        related_name="kb_entry"
    )
    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE
    )

    category = models.CharField(max_length=100)

    title = models.CharField(max_length=255)
    description = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    
class LiveSession(models.Model):
    PROVIDER_CHOICES = [
        ("meet", "Google Meet"),
        ("zoom", "Zoom"),
        ("teams", "Microsoft Teams"),
    ]

    STATUS_CHOICES = [
        ("created", "Created"),
        ("ended", "Ended"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    expert = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="live_sessions_as_expert"
    )

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="live_sessions_as_client"
    )

    provider = models.CharField(
        max_length=10,
        choices=PROVIDER_CHOICES,
        default="meet"
    )

    meeting_link = models.URLField(blank=True, null=True)

    duration = models.PositiveIntegerField(default=30)  # 10 / 30 / 60

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="created"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    ended_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.provider} session: {self.client} → {self.expert}"
    
    
# =====================================
# 📅 AVAILABILITY SLOT
# =====================================
class AvailabilitySlot(models.Model):
    
    UNIT_CHOICES = [
        ("hour", "Per Hour"),
        ("session", "Per Session"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    expert = models.ForeignKey(User, on_delete=models.CASCADE)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default="USD")
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default="hour")

    description = models.CharField(max_length=255, blank=True)

    is_booked = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.expert} | {self.start_time} - {self.end_time}"

    # ✅ INSTANCE METHOD (correct way)
    def is_owner(self, user):
        return self.expert.id == user.id


# =====================================
# 📹 BOOKING (AUTO JITSI MEETING)
# =====================================
        
class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    slot = models.ForeignKey(
        "AvailabilitySlot",
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    booked_by = models.ForeignKey("User", on_delete=models.CASCADE)

    meeting_link = models.URLField(blank=True, editable=False)
    details = models.TextField(blank=True)

    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["slot"],
                condition=Q(is_cancelled=False),
                name="unique_active_booking_per_slot"
            )
        ]

    def generate_meeting_link(self):
        return f"https://meet.jit.si/FancyLearn-{self.id}"

    def save(self, *args, **kwargs):
        # generate link only for active bookings
        if not self.is_cancelled and not self.meeting_link:
            super().save(*args, **kwargs)
            self.meeting_link = self.generate_meeting_link()
            super().save(update_fields=["meeting_link"])
            return

        super().save(*args, **kwargs)

    def cancel(self):
        if self.is_cancelled:
            return

        self.is_cancelled = True
        self.cancelled_at = timezone.now()
        self.meeting_link = ""
        self.save(update_fields=["is_cancelled", "cancelled_at", "meeting_link"])
        
        
class Review(models.Model):

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)

    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_reviews")
    reviewed_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_reviews")

    rating = models.IntegerField()
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    

class SendEmail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_emails'
    )

    recipient = models.EmailField()

    subject = models.CharField(max_length=255)
    body = models.TextField()  # HTML content (Quill)

    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} → {self.recipient}"
    
    
class UserReport(models.Model):

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reports_sent"
    )

    reported_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reports_received"
    )

    reason = models.TextField()

    evidence_image = models.ImageField(
        upload_to="reports/evidence/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reporter} reported {self.reported_user}"