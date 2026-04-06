from django.db import transaction
from django.db.models import F

from MindBridge.models import Tip, Answer, Payment


class PaymentService:

    @staticmethod
    @transaction.atomic
    def send_tip(sender, answer, amount):

        Tip.objects.create(
            sender=sender,
            receiver=answer.author,
            answer=answer,
            amount=amount
        )

        Answer.objects.filter(id=answer.id).update(
            tips_received=F("tips_received") + amount
        )

        Payment.objects.create(
            user=sender,
            amount=amount,
            payment_type="tip",
            reference_id="TIP",
            status="completed"
        )