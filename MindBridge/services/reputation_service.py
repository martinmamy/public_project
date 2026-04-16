from django.db import transaction
from django.db.models import F, Sum
from datetime import date

from MindBridge.models import User, ReputationLog


class ReputationService:
    """
    Advanced Reputation Service:
    - Supports different actions with varying points
    - Daily limits per user
    - Tier system
    - Logging all activities
    """

    # Default points mapping
    POINTS = {
        "answer_upvote": 2,
        "question_upvote": 5,
        "accepted_answer": 10,
        "bounty_award": 50,
        "comment_upvote": 1,
        "post_creation": 1,
        "daily_bonus": 5
    }

    # Maximum points per user per day
    DAILY_MAX = 200

    # Reputation tiers
    TIERS = [
        (0, "Beginner"),
        (100, "Contributor"),
        (500, "Advanced"),
        (1000, "Expert"),
        (5000, "Master Expert")
    ]

    @staticmethod
    def calculate_tier(reputation_score):
        """Return tier name based on reputation score."""
        tier_name = "Newbie"
        for threshold, name in sorted(ReputationService.TIERS, key=lambda x: x[0]):
            if reputation_score >= threshold:
                tier_name = name
        return tier_name

    @staticmethod
    def get_daily_total(user, today=None):
        """Return total reputation earned today."""
        today = today or date.today()
        total = ReputationLog.objects.filter(user=user, created_at__date=today).aggregate(
            total=Sum("points")
        )["total"] or 0
        return total

    @staticmethod
    @transaction.atomic
    def award_points(user, action, reason=None, points=None):
        """
        Award points to a user for a specific action.
        """
        if not points:
            points = ReputationService.POINTS.get(action, 0)

        # Enforce daily maximum
        today_total = ReputationService.get_daily_total(user)
        points = min(points, max(ReputationService.DAILY_MAX - today_total, 0))
        if points <= 0:
            return None  # Daily limit reached

        # Update user reputation safely
        User.objects.filter(id=user.id).update(
            reputation_score=F("reputation_score") + points
        )

        # Log the reputation event
        ReputationLog.objects.create(
            user=user,
            points=points,
            action=action,
            reason=reason or f"{action} points awarded"
        )

        # Optional: return new tier
        user.refresh_from_db()
        return {
            "new_score": user.reputation_score,
            "tier": ReputationService.calculate_tier(user.reputation_score),
            "points_awarded": points
        }