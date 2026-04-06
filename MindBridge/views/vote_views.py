import json
from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from MindBridge.services.expert_verification_service import ExpertVerificationService
from MindBridge.services.notification_service import NotificationService
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from MindBridge.models import Problem, Answer
from MindBridge.services.vote_service import VoteService


@method_decorator(login_required, name="dispatch")
class VoteProblemView(View):

    def post(self, request, problem_id):

        problem = get_object_or_404(Problem, id=problem_id)

        data = json.loads(request.body)

        VoteService.vote_problem(
            request.user,
            problem,
            data["value"]
        )

        problem.refresh_from_db()

        return JsonResponse({
            "status": "voted",
            "score": problem.votes_score
        })


@method_decorator(login_required, name="dispatch")
class VoteAnswerView(View):

    def post(self, request, answer_id):

        answer = get_object_or_404(
            Answer.objects.select_related("author", "problem"),
            id=answer_id
        )

        try:
            data = json.loads(request.body)
            vote_value = data.get("value")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid_json"}, status=400)

        # Process vote
        VoteService.vote_answer(
            request.user,
            answer,
            vote_value
        )

        # Refresh vote score
        answer.refresh_from_db()

        # -----------------------------
        # Auto expert verification
        # -----------------------------
        result = ExpertVerificationService.verify_user(answer.author)

        if result == "verified":
            NotificationService.create_notification(
                user=answer.author,
                message="🎉 Congratulations! You are now a Verified Expert.",
                url=reverse("profile", args=[answer.author.id])
            )

        return JsonResponse({
            "status": "voted",
            "score": answer.votes_score
        })

