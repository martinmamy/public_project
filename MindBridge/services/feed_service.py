from django.db.models import F, Count, Q
from MindBridge.models import Problem, Follow, User, Bounty, Tip


# =====================================================
# GLOBAL FEED (Problems created by logged-in user)
# =====================================================
def get_global_feed(user, limit=20, year=None, month=None):

    qs = Problem.objects.filter(author=user).select_related("author").annotate(
        answers_total=Count("answers", distinct=True),
        vote_score=F("votes_score"),
        views=F("views_count")
    ).order_by("-created_at")

    if year:
        qs = qs.filter(created_at__year=int(year))

    if month:
        qs = qs.filter(created_at__month=int(month))

    return qs[:limit]


# =====================================================
# TRENDING FEED (Top problems created by the user)
# Ranking based on votes + answers + views
# =====================================================
def get_trending_feed(user, limit=10, year=None, month=None):

    qs = Problem.objects.filter(author=user).select_related("author").annotate(

        answers_total=Count("answers", distinct=True),
        vote_score=F("votes_score"),
        views=F("views_count"),

        trending_score=(
            F("votes_score") +
            Count("answers", distinct=True) +
            F("views_count")
        )
    )

    if year:
        qs = qs.filter(created_at__year=int(year))

    if month:
        qs = qs.filter(created_at__month=int(month))

    return qs.order_by("-trending_score")[:limit]


# =====================================================
# FOLLOWERS FEED
# Users who follow the logged-in user
# =====================================================
def get_followers_feed(user, limit=None, year=None, month=None):

    qs = User.objects.filter(
        id__in=Follow.objects.filter(
            following=user
        ).values_list("follower_id", flat=True)
    ).order_by("-date_joined")

    if year:
        qs = qs.filter(date_joined__year=int(year))

    if month:
        qs = qs.filter(date_joined__month=int(month))

    if limit:
        qs = qs[:limit]

    return list(qs)


# =====================================================
# FOLLOWING FEED
# Users the logged-in user follows
# =====================================================
def get_following_feed(user, limit=None, year=None, month=None):

    qs = User.objects.filter(
        id__in=Follow.objects.filter(
            follower=user
        ).values_list("following_id", flat=True)
    ).order_by("-date_joined")

    if year:
        qs = qs.filter(date_joined__year=int(year))

    if month:
        qs = qs.filter(date_joined__month=int(month))

    if limit:
        qs = qs[:limit]

    return list(qs)


# =====================================================
# PERSONALIZED FEED
# Problems from followed users
# BUT only if the logged-in user interacted
# (commented OR voted)
# =====================================================
def get_personalized_feed(user, limit=20, year=None, month=None):
    """
    Returns problems from users the logged-in user follows,
    BUT only if the logged-in user interacted (commented or voted)
    """

    followed_users = Follow.objects.filter(
        follower=user
    ).values_list("following_id", flat=True)

    # Ensure Vote model exists and is related to Problem
    qs = Problem.objects.filter(
        author_id__in=followed_users
    ).filter(
        Q(answers__author=user) | Q(vote__user=user)  # <-- use the correct related_name from Vote model
    ).select_related("author").annotate(
        answers_total=Count("answers", distinct=True),
        vote_score=F("votes_score"),
        views=F("views_count")
    ).distinct().order_by("-created_at")

    if year:
        qs = qs.filter(created_at__year=int(year))
    if month:
        qs = qs.filter(created_at__month=int(month))

    return qs[:limit]


from django.db.models import Sum
from django.db.models.functions import TruncDate

def get_tips_analytics(user, year=None, month=None):
    """
    Returns:
    - earnings (tips received)
    - spending (tips sent)
    Grouped by date (for graph)
    """

    earnings = Tip.objects.filter(receiver=user)
    spending = Tip.objects.filter(sender=user)

    if year:
        earnings = earnings.filter(created_at__year=int(year))
        spending = spending.filter(created_at__year=int(year))

    if month:
        earnings = earnings.filter(created_at__month=int(month))
        spending = spending.filter(created_at__month=int(month))

    earnings = earnings.annotate(
        date=TruncDate("created_at")
    ).values("date").annotate(
        total=Sum("amount")
    ).order_by("date")

    spending = spending.annotate(
        date=TruncDate("created_at")
    ).values("date").annotate(
        total=Sum("amount")
    ).order_by("date")

    return {
        "earnings": list(earnings),
        "spending": list(spending),
    }



def get_bounties_analytics(user, year=None, month=None):
    """
    - earnings: bounties won
    - spending: bounties created
    """

    earnings = Bounty.objects.filter(awarded_to=user)
    spending = Bounty.objects.filter(creator=user)

    if year:
        earnings = earnings.filter(created_at__year=int(year))
        spending = spending.filter(created_at__year=int(year))

    if month:
        earnings = earnings.filter(created_at__month=int(month))
        spending = spending.filter(created_at__month=int(month))

    earnings = earnings.annotate(
        date=TruncDate("created_at")
    ).values("date").annotate(
        total=Sum("amount")
    ).order_by("date")

    spending = spending.annotate(
        date=TruncDate("created_at")
    ).values("date").annotate(
        total=Sum("amount")
    ).order_by("date")

    return {
        "earnings": list(earnings),
        "spending": list(spending),
    }
    
def get_financial_summary(user):
    tips_earned = Tip.objects.filter(receiver=user).aggregate(total=Sum("amount"))["total"] or 0
    tips_spent = Tip.objects.filter(sender=user).aggregate(total=Sum("amount"))["total"] or 0

    bounties_earned = Bounty.objects.filter(awarded_to=user).aggregate(total=Sum("amount"))["total"] or 0
    bounties_spent = Bounty.objects.filter(creator=user).aggregate(total=Sum("amount"))["total"] or 0

    return {
        "tips": {
            "earned": tips_earned,
            "spent": tips_spent,
            "net": tips_earned - tips_spent,   # ✅ ADD THIS
        },
        "bounties": {
            "earned": bounties_earned,
            "spent": bounties_spent,
            "net": bounties_earned - bounties_spent,  # ✅ ADD THIS
        }
    }