import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db.models import Q, F
from MindBridge.predefined import PREDEFINED_CATEGORIES
from django.utils import timezone
from datetime import timedelta


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

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    website = models.URLField(blank=True)

    country = models.CharField(max_length=100, db_index=True)

    profession = models.CharField(max_length=150, db_index=True)

    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["country"]),
            models.Index(fields=["profession"]),
        ]


class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=128)  # hashed
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() - self.created_at < timedelta(minutes=5)
    
# =========================================================
# 5. PROBLEM (MAIN POST)
# =========================================================

class Problem(models.Model):
    POST_TYPE_CHOICES = [
        ("issue", "Issue"),
        ("information", "Information"),
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

class CreatorSubscription(models.Model):

    creator = models.ForeignKey(
        User,
        related_name="creator_subscribers",
        on_delete=models.CASCADE
    )

    subscriber = models.ForeignKey(
        User,
        related_name="subscriptions",
        on_delete=models.CASCADE
    )

    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)

    active = models.BooleanField(default=True)

    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["creator", "subscriber"],
                name="unique_creator_subscription"
            )
        ]


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
        ("pending", "Pending"),
        ("active", "Active"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    advertiser = models.ForeignKey(
        User, 
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="ads"
    )

    advertiser_name = models.CharField(max_length=200)
    image = models.ImageField(upload_to="ads/", validators=[validate_file_size])
    target_url = models.URLField()

    category = models.ForeignKey(
        "MindBridge.Problem",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="ads"
    )

    price = models.DecimalField(max_digits=6, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=7)

    start_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)



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
        ],
        db_index=True
    )

    reference_id = models.CharField(max_length=200, unique=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    

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