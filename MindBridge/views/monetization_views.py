import json
from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from MindBridge.models import Answer
from MindBridge.services.payment_service import PaymentService


@method_decorator(login_required, name="dispatch")
class SendTipView(View):

    def post(self, request, answer_id):

        answer = get_object_or_404(Answer, id=answer_id)

        data = json.loads(request.body)

        PaymentService.send_tip(
            sender=request.user,
            answer=answer,
            amount=data["amount"]
        )

        return JsonResponse({"status": "tip_sent"})
    
    