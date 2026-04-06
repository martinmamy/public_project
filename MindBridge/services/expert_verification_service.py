from django.shortcuts import render, redirect
from django.contrib import messages
from MindBridge.models import Answer, User


class ExpertVerificationService:

    MIN_REPUTATION = 500
    MIN_ACCEPTED_ANSWERS = 5
    MIN_TOP_VOTED = 10
    VERIFICATION_FEE = 15  # USD

    @staticmethod
    def eligibility_status(user):
        """
        Check if the user meets the basic criteria for verification.
        Returns a dict with details and eligibility flag.
        """
        accepted_answers = Answer.objects.filter(author=user, is_accepted=True).count()
        top_answers_count = Answer.objects.filter(author=user).order_by("-votes_score")[:ExpertVerificationService.MIN_TOP_VOTED].count()

        qualifies = (
            user.reputation_score >= ExpertVerificationService.MIN_REPUTATION
            and accepted_answers >= ExpertVerificationService.MIN_ACCEPTED_ANSWERS
            and top_answers_count >= ExpertVerificationService.MIN_TOP_VOTED
        )

        return {
            "qualifies": qualifies,
            "reputation": user.reputation_score,
            "accepted_answers": accepted_answers,
            "top_answers_count": top_answers_count,
            "required_reputation": ExpertVerificationService.MIN_REPUTATION,
            "required_accepted": ExpertVerificationService.MIN_ACCEPTED_ANSWERS,
            "required_top_voted": ExpertVerificationService.MIN_TOP_VOTED,
            "verification_fee": ExpertVerificationService.VERIFICATION_FEE
        }

    @staticmethod
    def verify_user(user):
        """
        Automatically verify the user (manual or paid verification).
        Only works if user meets criteria.
        """
        status = ExpertVerificationService.eligibility_status(user)
        if status["qualifies"] and not user.is_verified_expert:
            user.is_verified_expert = True
            user.save(update_fields=["is_verified_expert"])
            return True
        return False