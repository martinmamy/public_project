# views.py
from django.views.generic import TemplateView
from django.db.models import Count, Sum
from django.utils.timezone import now
from MindBridge.models import Payment, User
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from django.shortcuts import get_object_or_404


class PaymentReportView(TemplateView):
    template_name = "report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_year = now().year

        # -------------------------
        # TAB 1: ALL TRANSACTIONS
        # -------------------------
        context["payments"] = Payment.objects.select_related("user").order_by("-created_at")

        # -------------------------
        # TAB 2: QUALIFIED USERS
        # -------------------------
        yearly_data = (
            Payment.objects
            .filter(created_at__year=current_year, status="completed")
            .values("user")
            .annotate(
                total_transactions=Count("id"),
                total_amount=Sum("amount")
            )
        )

        qualified_users = [
            data for data in yearly_data
            if data["total_transactions"] >= 30 or data["total_amount"] >= 2000
        ]

        # Attach user objects
        user_ids = [u["user"] for u in qualified_users]
        users = User.objects.filter(id__in=user_ids)

        # Map user -> stats
        user_stats = []
        for user in users:
            data = next((u for u in qualified_users if u["user"] == user.id), None)
            if data:
                user_stats.append({
                    "user": user,
                    "transactions": data["total_transactions"],
                    "amount": data["total_amount"]
                })

        context["qualified_users"] = user_stats

        return context
    


def download_user_report(request, user_id):
    user = get_object_or_404(User, id=user_id)

    payments = Payment.objects.filter(user=user, status="completed")

    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="{user.username}_report.pdf"'

    doc = SimpleDocTemplate(response)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph(f"User Report: {user.username}", styles["Title"]))

    for p in payments:
        content.append(
            Paragraph(
                f"{p.created_at.date()} - ${p.amount} ({p.payment_type})",
                styles["Normal"]
            )
        )

    doc.build(content)

    return response