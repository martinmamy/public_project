from django.db.models import (
    Count,
    Q,
    Value,
    IntegerField,
    Case,
    When
)
from django.utils import timezone

from MindBridge.models import Problem, User, CreatorsSubscription, Advertisement
from MindBridge.services.reputation_service import ReputationService



def sidebar_data(request):

    now = timezone.now()

    # -----------------------------------------
    # TRENDING UNSOLVED PROBLEMS
    # -----------------------------------------
    trending_problems = (
        Problem.objects
        .select_related("author")
        .prefetch_related("answers")
        .annotate(

            # Count accepted answers
            accepted_answers_count=Count(
                "answers",
                filter=Q(answers__is_accepted=True),
                distinct=True
            ),

            # Promotion priority
            promotion_priority=Case(

                When(
                    promotions__promotion_type="pinned",
                    promotions__expires_at__gt=now,
                    then=Value(3)
                ),

                When(
                    promotions__promotion_type="boosted",
                    promotions__expires_at__gt=now,
                    then=Value(2)
                ),

                When(
                    promotions__promotion_type="featured",
                    promotions__expires_at__gt=now,
                    then=Value(1)
                ),

                default=Value(0),
                output_field=IntegerField()
            ),
        )

        # Only problems WITHOUT accepted answers
        .filter(accepted_answers_count=0)

        # Remove duplicates caused by joins
        .distinct()

        .order_by(
            "-promotion_priority",
            "-views_count",
            "-votes_score",
            "-created_at"
        )[:10]
    )

    # -----------------------------------------
    # SUGGESTED EXPERTS
    # -----------------------------------------
    suggested_experts = (
        User.objects
        .filter(is_verified_expert=True)
        .order_by("-reputation_score")[:10]
    )

    for expert in suggested_experts:
        expert.tier = ReputationService.calculate_tier(
            expert.reputation_score or 0
        )

    return {
        "trendings_problems": trending_problems,
        "suggested_experts": suggested_experts,
    }
    
    


def subscription_status(request):

    has_active_subscription = False

    if request.user.is_authenticated:

        has_active_subscription = (
            request.user.is_superuser
            or
            CreatorsSubscription.objects.filter(
                user=request.user,
                active=True,
                status=CreatorsSubscription.Status.ACTIVE,
            ).exists()
        )

    return {
        "has_active_subscription": has_active_subscription
    }
    


def ads_context(request):
    now = timezone.now()

    active_problem_ids = Advertisement.objects.filter(
        status="active",
        is_deleted=False,
        expires_at__gt=now,
        related_problem__isnull=False
    ).values_list("related_problem_id", flat=True).distinct()

    return {
        "ACTIVE_AD_PROBLEM_IDS": set(str(i) for i in active_problem_ids)
    }