from django.db import transaction
from django.db.models import F

from MindBridge.models import Answer, Problem
from .reputation_service import ReputationService
from .notification_service import NotificationService


class AnswerService:

    @staticmethod
    @transaction.atomic
    def create_answer(author, problem, content):
        answer = Answer.objects.create(
            author=author,
            problem=problem,
            content=content
        )

        # Increment problem's answers count
        Problem.objects.filter(id=problem.id).update(
            answers_count=F("answers_count") + 1
        )

        # Notify problem author about new answer
        NotificationService.notify_problem_author_new_answer(problem, answer)

        return answer

    @staticmethod
    @transaction.atomic
    def accept_answer(answer):
        problem = answer.problem

        if problem.is_solved:
            raise Exception("Problem already solved")

        # Mark this answer as accepted
        answer.is_accepted = True
        answer.save(update_fields=["is_accepted"])

        # Mark the problem as solved
        problem.is_solved = True
        problem.save(update_fields=["is_solved"])

        # Award reputation points to the answer author
        ReputationService.award_points(
            user=answer.author,
            points=10,
            reason="Accepted answer"
        )

        # Notify the answer author using the existing create_notification method
        NotificationService.create_notification(
            user=answer.author,
            message=f"Your answer to '{problem.title}' was accepted!",
            url=f"/problems/{problem.id}/"
        )

        # Optionally, handle bounty if problem has one
        if problem.bounty_amount > 0:
            answer.author.received_bounties += problem.bounty_amount
            answer.author.save(update_fields=["received_bounties"])

            NotificationService.create_notification(
                user=answer.author,
                message=f"You received a ${problem.bounty_amount} bounty for solving '{problem.title}'!",
                url=f"/problems/{problem.id}/"
            )

        return answer