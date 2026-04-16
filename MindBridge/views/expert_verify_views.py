from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from MindBridge.models import Answer, User
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from MindBridge.services.expert_verification_service import ExpertVerificationService


# ==============================
# VERIFY EXPERT VIEW
# ==============================

@method_decorator(login_required, name="dispatch")
class VerifyExpertView(View):
    template_name = "verify_expert.html"

    def get(self, request):
        status = ExpertVerificationService.eligibility_status(request.user)
        return render(request, self.template_name, {"status": status})

    def post(self, request):
        status = ExpertVerificationService.eligibility_status(request.user)

        if not status["qualifies"]:
            messages.error(
                request,
                "You do not meet the criteria for expert verification yet. "
                f"Required: {status['required_reputation']} reputation, "
                f"{status['required_accepted']} accepted answers, "
                f"{status['required_top_voted']} top voted answers."
            )
            return redirect("verify_expert")

        # Check if user has linked PayPal
        if not hasattr(request.user, "paypal_account"):
            messages.warning(request, "You must link your PayPal account to pay the verification fee.")
            return redirect("link_payment_account")

        # Optionally, here you can call your payment service
        # Example: if payment succeeds:
        payment_successful = True  # Replace with actual PayPal payment logic
        if payment_successful:
            ExpertVerificationService.verify_user(request.user)
            messages.success(request, "Congratulations! You are now a verified expert.")
            return redirect("profile")  # or wherever
        else:
            messages.error(request, "Payment failed. Verification not completed.")
            return redirect("verify_expert")
        
        
@method_decorator(login_required, name="dispatch")
class AjaxVerifyExpertView(View):
    """
    Handle expert verification via AJAX from profile page.
    Ensures user has PayPal linked and enough balance to pay the fee.
    """
    def post(self, request, user_id):
        # Ensure the request is from the profile owner
        if request.user.id != user_id:
            return JsonResponse({"success": False, "error": "Unauthorized"}, status=403)

        # Eligibility check
        status = ExpertVerificationService.eligibility_status(request.user)
        if not status["qualifies"]:
            return JsonResponse({
                "success": False,
                "error": "You do not meet the criteria for verification yet.",
                "details": status
            }, status=403)

        # Check PayPal linked
        if not hasattr(request.user, "paypal_account"):
            return JsonResponse({
                "success": False,
                "error": "You must link your PayPal account to pay the verification fee."
            }, status=403)

        # Check user balance
        user_balance = getattr(request.user, "wallet_balance", 0)
        fee = status["verification_fee"]
        if user_balance < fee:
            return JsonResponse({
                "success": False,
                "error": f"Insufficient balance. You need ${fee}, but have ${user_balance}."
            }, status=403)

        # -----------------------------
        # Deduct fee from wallet
        # -----------------------------
        request.user.wallet_balance -= fee
        request.user.save(update_fields=["wallet_balance"])

        # Verify the user
        verified = ExpertVerificationService.verify_user(request.user)
        if verified:
            return JsonResponse({
                "success": True,
                "message": "Congratulations! You are now a verified expert.",
                "new_balance": request.user.wallet_balance
            }, status=200)
        else:
            return JsonResponse({
                "success": False,
                "error": "You are already verified or verification failed."
            }, status=403)