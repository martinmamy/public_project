from django.db import transaction
from django.db.models import F

from MindBridge.models import Vote, Problem, Answer
from .reputation_service import ReputationService


class VoteService:

    @staticmethod
    @transaction.atomic
    def vote_problem(user, problem, value):

        vote, created = Vote.objects.get_or_create(
            user=user,
            problem=problem,
            defaults={"value": value}
        )

        if not created:
            if vote.value == value:
                return vote
            vote.value = value
            vote.save(update_fields=["value"])

        Problem.objects.filter(id=problem.id).update(
            votes_score=F("votes_score") + value
        )

        ReputationService.award_points(problem.author, 2 * value, "Problem vote")

        return vote


    @staticmethod
    @transaction.atomic
    def vote_answer(user, answer, value):

        vote, created = Vote.objects.get_or_create(
            user=user,
            answer=answer,
            defaults={"value": value}
        )

        if not created:
            if vote.value == value:
                return vote
            vote.value = value
            vote.save(update_fields=["value"])

        Answer.objects.filter(id=answer.id).update(
            votes_score=F("votes_score") + value
        )

        ReputationService.award_points(answer.author, 5 * value, "Answer vote")

        return vote