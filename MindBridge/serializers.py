from rest_framework import serializers
from MindBridge.models import CreatorsSubscription


class CreatorSubscriptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = CreatorsSubscription

        fields = (
            "uuid",
            "user",
            "plan",
            "amount",
            "currency",
            "status",
            "active",
            "premium_access",
            "paypal_subscription_id",
            "paypal_plan_id",
            "started_at",
            "next_billing_time",
            "cancelled_at",
            "expired_at",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "uuid",
            "status",
            "active",
            "premium_access",
            "paypal_subscription_id",
            "paypal_plan_id",
            "started_at",
            "next_billing_time",
            "cancelled_at",
            "expired_at",
            "created_at",
            "updated_at",
        )

    # =========================================================
    # VALIDATION
    # =========================================================

    def validate(self, attrs):

        plan = attrs.get("plan")
        amount = attrs.get("amount")

        if plan == CreatorsSubscription.Plan.MONTHLY and amount <= 0:
            raise serializers.ValidationError(
                "Monthly plan must have a valid amount."
            )

        if plan == CreatorsSubscription.Plan.YEARLY and amount <= 0:
            raise serializers.ValidationError(
                "Yearly plan must have a valid amount."
            )

        return attrs

    # =========================================================
    # CREATE (force user from request)
    # =========================================================

    def create(self, validated_data):

        request = self.context.get("request")

        validated_data["user"] = request.user

        # force safe defaults (PayPal controls lifecycle)
        validated_data["status"] = CreatorsSubscription.Status.PENDING
        validated_data["active"] = False
        validated_data["premium_access"] = False

        return super().create(validated_data)