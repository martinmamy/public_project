from django.db.models import (
    Count,
    Q,
    Value,
    IntegerField,
    Case,
    When
)
from django.utils import timezone

from MindBridge.models import Problem, User


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
        )[:20]
    )

    # -----------------------------------------
    # SUGGESTED EXPERTS
    # -----------------------------------------
    suggested_experts = (
        User.objects
        .filter(is_verified_expert=True)
        .order_by("-reputation_score")[:20]
    )

    return {
        "trendings_problems": trending_problems,
        "suggested_experts": suggested_experts,
    }