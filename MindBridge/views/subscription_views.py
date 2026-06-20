import json

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from MindBridge.models import CreatorsSubscription
from MindBridge.services.paypal_services import PayPalClient


# =========================================================
# CREATE PLATFORM SUBSCRIPTION
# =========================================================

@method_decorator(login_required, name="dispatch")
class CreateSubscriptionAPIView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):

        # -------------------------------------------------
        # BLOCK MULTIPLE ACTIVE SUBSCRIPTIONS
        # -------------------------------------------------

        if CreatorsSubscription.objects.filter(
            user=request.user,
            active=True
        ).exists():

            return Response(
                {"detail": "You already have an active premium subscription."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # -------------------------------------------------
        # PLAN SELECTION
        # -------------------------------------------------

        selected_plan = request.data.get("plan", "monthly").lower()

        if selected_plan == "yearly":

            plan = CreatorsSubscription.Plan.YEARLY
            paypal_plan_id = settings.PAYPAL_ANNUAL_PLAN_ID
            amount = settings.YEARLY_SUBSCRIPTION_PRICE

        else:

            plan = CreatorsSubscription.Plan.MONTHLY
            paypal_plan_id = settings.PAYPAL_MONTHLY_PLAN_ID
            amount = settings.MONTHLY_SUBSCRIPTION_PRICE

        if not paypal_plan_id:

            return Response(
                {"detail": "Subscription plan unavailable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # -------------------------------------------------
        # CREATE PAYPAL SUBSCRIPTION
        # -------------------------------------------------

        try:

            paypal_response = PayPalClient.create_subscription(
                plan_id=paypal_plan_id,
                return_url=request.build_absolute_uri(
                    reverse("paypal-subscription-success")
                ),
                cancel_url=request.build_absolute_uri(
                    reverse("paypal-subscription-cancel")
                ),
                subscriber_email=request.user.email,
            )

        except Exception as e:

            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # -------------------------------------------------
        # GET APPROVAL URL
        # -------------------------------------------------

        approval_url = next(
            (
                link["href"]
                for link in paypal_response.get("links", [])
                if link["rel"] == "approve"
            ),
            None
        )

        if not approval_url:

            return Response(
                {"detail": "Unable to generate PayPal approval URL."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # -------------------------------------------------
        # CLEAN OLD PENDING SUBSCRIPTIONS
        # -------------------------------------------------

        CreatorsSubscription.objects.filter(
            user=request.user,
            active=False
        ).delete()

        # -------------------------------------------------
        # CREATE LOCAL SUBSCRIPTION
        # -------------------------------------------------

        subscription = CreatorsSubscription.objects.create(
            user=request.user,
            paypal_subscription_id=paypal_response["id"],
            paypal_plan_id=paypal_plan_id,
            plan=plan,
            amount=amount,
            status=CreatorsSubscription.Status.SUSPENDED,
            active=False,
            premium_access=False,
        )

        return Response(
            {
                "approval_url": approval_url,
                "subscription_uuid": str(subscription.uuid),
            },
            status=status.HTTP_201_CREATED
        )


# =========================================================
# CANCEL SUBSCRIPTION
# =========================================================

@method_decorator(login_required, name="dispatch")
class CancelSubscriptionAPIView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, uuid):

        subscription = CreatorsSubscription.objects.filter(
            uuid=uuid,
            user=request.user
        ).first()

        if not subscription:

            return Response(
                {"detail": "Subscription not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not subscription.active:

            return Response(
                {"detail": "Subscription already inactive."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not subscription.paypal_subscription_id:

            return Response(
                {"detail": "Missing PayPal subscription ID."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            PayPalClient.cancel_subscription(
                subscription.paypal_subscription_id
            )

        except Exception as e:

            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        subscription.status = CreatorsSubscription.Status.CANCELLED
        subscription.active = False
        subscription.cancelled_at = timezone.now()
        subscription.save()

        return Response(
            {"detail": "Subscription cancelled successfully."},
            status=status.HTTP_200_OK
        )


# =========================================================
# PAYPAL WEBHOOK
# =========================================================

class PayPalWebhookAPIView(APIView):

    authentication_classes = []
    permission_classes = []

    def post(self, request):

        payload = request.data

        event_type = payload.get("event_type")
        resource = payload.get("resource", {})

        subscription_id = resource.get("id")

        if not subscription_id:
            return HttpResponse(status=200)

        subscription = CreatorsSubscription.objects.filter(
            paypal_subscription_id=subscription_id
        ).first()

        if not subscription:
            return HttpResponse(status=200)

        billing_info = resource.get("billing_info", {})
        next_billing_time = billing_info.get("next_billing_time")

        if next_billing_time:
            subscription.next_billing_time = next_billing_time

        # -------------------------------------------------
        # ACTIVATE
        # -------------------------------------------------

        if event_type in [
            "BILLING.SUBSCRIPTION.ACTIVATED",
            "PAYMENT.SALE.COMPLETED"
        ]:
            subscription.status = CreatorsSubscription.Status.ACTIVE
            subscription.active = True
            subscription.premium_access = True

        # -------------------------------------------------
        # CANCEL
        # -------------------------------------------------

        elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
            subscription.status = CreatorsSubscription.Status.CANCELLED
            subscription.active = False
            subscription.premium_access = False
            subscription.cancelled_at = timezone.now()

        # -------------------------------------------------
        # SUSPEND
        # -------------------------------------------------

        elif event_type == "BILLING.SUBSCRIPTION.SUSPENDED":
            subscription.status = CreatorsSubscription.Status.SUSPENDED
            subscription.active = False
            subscription.premium_access = False

        # -------------------------------------------------
        # EXPIRE
        # -------------------------------------------------

        elif event_type == "BILLING.SUBSCRIPTION.EXPIRED":
            subscription.status = CreatorsSubscription.Status.EXPIRED
            subscription.active = False
            subscription.premium_access = False

        subscription.updated_at = timezone.now()
        subscription.save()

        return HttpResponse(status=200)


# =========================================================
# SUCCESS / CANCEL PAGES
# =========================================================

@method_decorator(login_required, name="dispatch")
class PayPalSubscriptionSuccessView(TemplateView):
    template_name = "subscriptions_success.html"


@method_decorator(login_required, name="dispatch")
class PayPalSubscriptionCancelView(TemplateView):
    template_name = "subscriptions_cancel.html"


# =========================================================
# CHECKOUT PAGE (FIXED - NO creator_id)
# =========================================================

@method_decorator(login_required, name="dispatch")
class SubscriptionCheckoutPageView(TemplateView):

    template_name = "choose_subscription.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        subscription = CreatorsSubscription.objects.filter(
            user=self.request.user
        ).first()

        context["subscription"] = subscription

        context["monthly_price"] = settings.MONTHLY_SUBSCRIPTION_PRICE
        context["yearly_price"] = settings.YEARLY_SUBSCRIPTION_PRICE

        return context