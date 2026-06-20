import json

from django.views.generic import FormView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.auth import get_user_model

from MindBridge.forms import AdminSendEmailForm
from MindBridge.models import SendEmail

User = get_user_model()


class AdminSendEmailView(LoginRequiredMixin, FormView):
    template_name = "admins/send_workspace_email.html"
    form_class = AdminSendEmailForm
    success_url = reverse_lazy("admin_send_email")

    # =====================================================
    # USER QUERYSET
    # =====================================================
    def get_user_queryset(self):
        return (
            User.objects
            .filter(
                is_active=True,
                is_staff=False,
                is_superuser=False
            )
            .exclude(email__isnull=True)
            .exclude(email="")
            .exclude(email__icontains="admin")
        )

    # =====================================================
    # EMAIL LIST
    # =====================================================
    def get_all_emails(self):
        return list(
            self.get_user_queryset()
            .values_list("email", flat=True)
            .distinct()
        )

    # =====================================================
    # SEARCHABLE USER DATA
    # =====================================================
    def get_users_data(self):
        return [
            {
                "id": str(user["id"]),
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": user["email"],
            }
            for user in self.get_user_queryset().values(
                "id",
                "first_name",
                "last_name",
                "email",
            )
        ]

    # =====================================================
    # CONTEXT
    # =====================================================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["all_emails"] = json.dumps(
            self.get_all_emails()
        )

        context["users_data"] = json.dumps(
            self.get_users_data()
        )

        return context

    # =====================================================
    # FORM VALID
    # =====================================================
    def form_valid(self, form):

        subject = form.cleaned_data["subject"]
        body_html = form.cleaned_data["body"]

        send_to_all = form.cleaned_data.get(
            "send_to_all"
        )

        raw_recipient = form.cleaned_data.get(
            "recipient",
            ""
        )

        # =================================================
        # RECIPIENT RESOLUTION
        # =================================================
        if send_to_all:

            recipients = self.get_all_emails()

        else:

            recipients = [
                email.strip().lower()
                for email in raw_recipient.split(",")
                if email.strip()
            ]

        # remove duplicates while preserving order
        recipients = list(
            dict.fromkeys(recipients)
        )

        # =================================================
        # VALIDATION
        # =================================================
        if not recipients:

            form.add_error(
                None,
                "Please select at least one recipient."
            )

            return self.form_invalid(form)

        # =================================================
        # SEND EMAILS
        # =================================================
        sent_count = 0
        failed = []

        for email_address in recipients:

            try:

                msg = EmailMessage(
                    subject=subject,
                    body=body_html,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email_address],
                )

                msg.content_subtype = "html"

                msg.send(
                    fail_silently=False
                )

                SendEmail.objects.create(
                    admin_user=self.request.user,
                    recipient=email_address,
                    subject=subject,
                    body=body_html
                )

                sent_count += 1

            except Exception as e:

                failed.append(
                    f"{email_address}: {str(e)}"
                )

        # =================================================
        # SUCCESS MESSAGE
        # =================================================
        messages.success(
            self.request,
            f"✅ Email sent successfully to {sent_count} recipient(s)."
        )

        # =================================================
        # FAILURE MESSAGE
        # =================================================
        if failed:

            messages.warning(
                self.request,
                f"⚠ {len(failed)} email(s) failed to send."
            )

            for error in failed[:5]:
                messages.error(
                    self.request,
                    error
                )

        return super().form_valid(form)