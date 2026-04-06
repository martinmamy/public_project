from django.db import transaction
from django.db.models import F

from MindBridge.models import ProblemView, Problem


class AnalyticsService:

    @staticmethod
    @transaction.atomic
    def track_problem_view(problem, user=None, ip_address=None):

        ProblemView.objects.create(
            problem=problem,
            user=user,
            ip_address=ip_address
        )

        Problem.objects.filter(id=problem.id).update(
            views_count=F("views_count") + 1
        )


    @staticmethod
    def trending_problems():

        return Problem.objects.order_by(
            "-votes_score",
            "-answers_count",
            "-views_count"
        )[:50]