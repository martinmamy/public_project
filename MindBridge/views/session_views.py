from django.views.generic import CreateView, ListView, View
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.db.models import Exists, OuterRef
from MindBridge.models import AvailabilitySlot, Booking, Review
from MindBridge.services.notification_service import NotificationService
from django.utils.dateparse import parse_datetime


# =====================================
# 🔐 HELPERS
# =====================================

def is_owner(slot, user):
    return slot.expert_id == user.id


def parse_dt(value):
    return parse_datetime(value) if value else None


# =====================================
# 👨‍💻 CREATE SLOT
# =====================================
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware

@method_decorator(login_required, name="dispatch")
class AvailabilitySlotCreateView(LoginRequiredMixin, CreateView):
    model = AvailabilitySlot
    fields = ["start_time", "end_time", "price", "currency", "unit", "description"]
    template_name = "create_slot.html"

    def form_valid(self, form):
        form.instance.expert = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("slot_list", kwargs={"user_id": self.request.user.id})


from django.db.models import Exists, OuterRef, Case, When, BooleanField
from django.utils import timezone

from django.db.models import Exists, OuterRef, Case, When, BooleanField
from django.utils import timezone

@method_decorator(login_required, name="dispatch")
class SlotListView(LoginRequiredMixin, ListView):
    model = AvailabilitySlot
    template_name = "slot_list.html"
    context_object_name = "slots"

    def get_queryset(self):

        now = timezone.now()

        booked_qs = Booking.objects.filter(
            slot_id=OuterRef("pk"),
            is_cancelled=False
        )

        return (
            AvailabilitySlot.objects
            .filter(
                expert_id=self.kwargs["user_id"],
                end_time__gte=now   # 🔥 ONLY ACTIVE SLOTS
            )
            .annotate(has_booking=Exists(booked_qs))
            .order_by("start_time")
        )


from django.utils.timezone import is_naive, make_aware

@method_decorator(login_required, name="dispatch")
class SlotEventsAPIView(View):

    def get(self, request, *args, **kwargs):

        user_id = request.GET.get("user_id")
        if not user_id:
            return JsonResponse([], safe=False)

        slots = AvailabilitySlot.objects.filter(expert_id=user_id)

        data = []
        for slot in slots:

            color = "#22c55e"

            if slot.is_archived:
                color = "#9ca3af"
            elif Booking.objects.filter(slot=slot, is_cancelled=False).exists():
                color = "#ef4444"

            start = slot.start_time
            end = slot.end_time

            # 🔥 FORCE UTC ISO FORMAT WITH Z
            data.append({
                "id": str(slot.id),
                "title": slot.description or "Available Slot",

                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z"),

                "color": color,

                "extendedProps": {
                    "price": str(slot.price),
                    "currency": slot.currency,
                    "unit": slot.unit,
                    "description": slot.description,
                    "archived": slot.is_archived,
                }
            })

        return JsonResponse(data, safe=False)


from django.utils import timezone

@method_decorator(login_required, name="dispatch")
class SlotUpdateView(LoginRequiredMixin, View):

    def post(self, request, pk):

        now = timezone.now()

        slot = get_object_or_404(AvailabilitySlot, id=pk)

        if not slot.is_owner(request.user):
            return HttpResponseForbidden()

        # 🔥 SAME RULE AS LIST (hide expired)
        if slot.end_time <= now or slot.is_archived:
            messages.error(request, "This slot is expired and cannot be edited.")
            return redirect("slot_list", user_id=slot.expert_id)

        if slot.is_booked:
            messages.error(request, "Booked slot cannot be edited.")
            return redirect("slot_list", user_id=slot.expert_id)

        start = parse_datetime(request.POST.get("start_time"))
        end = parse_datetime(request.POST.get("end_time"))

        if not start or not end or start >= end:
            messages.error(request, "Invalid time range.")
            return redirect("slot_list", user_id=slot.expert_id)

        slot.start_time = start
        slot.end_time = end
        slot.price = request.POST.get("price", slot.price)
        slot.currency = request.POST.get("currency", slot.currency)
        slot.unit = request.POST.get("unit", slot.unit)
        slot.description = request.POST.get("description", "")

        slot.save()

        messages.success(request, "Slot updated successfully.")
        return redirect("slot_list", user_id=slot.expert_id)

# =====================================
# 🗑 DELETE SLOT (SAFE)
# =====================================
@method_decorator(login_required, name="dispatch")
class SlotDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):

        slot = get_object_or_404(AvailabilitySlot, id=pk)

        if not is_owner(slot, request.user):
            return HttpResponseForbidden()

        # block deletion if active booking exists
        if Booking.objects.filter(slot=slot, is_cancelled=False).exists():
            messages.error(request, "Cannot delete a booked slot.")
            return redirect("slot_list", user_id=slot.expert_id)

        slot.delete()

        messages.success(request, "Slot deleted.")
        return redirect("slot_list", user_id=slot.expert_id)


# =====================================
# 📅 BOOK SLOT (FULLY SAFE + ATOMIC)
# =====================================
@method_decorator(login_required, name="dispatch")
class BookingCreateView(LoginRequiredMixin, View):

    def post(self, request, slot_id):

        now = timezone.now()

        with transaction.atomic():

            # 🔒 LOCK SLOT
            slot = (
                AvailabilitySlot.objects
                .select_for_update()
                .get(id=slot_id)
            )

            # ❌ SELF BOOKING
            if slot.expert_id == request.user.id:
                messages.error(request, "You cannot book your own slot.")
                return redirect("slot_list", user_id=slot.expert_id)

            # ❌ EXPIRED
            if slot.end_time <= now:
                slot.is_archived = True
                slot.save(update_fields=["is_archived"])
                messages.error(request, "Slot has expired.")
                return redirect("slot_list", user_id=slot.expert_id)

            # ❌ TOO CLOSE
            if slot.start_time <= now + timedelta(minutes=5):
                messages.error(request, "Booking too close to start time.")
                return redirect("slot_list", user_id=slot.expert_id)

            # ❌ ALREADY BOOKED
            if Booking.objects.filter(slot=slot, is_cancelled=False).exists():
                messages.error(request, "This slot is already booked.")
                return redirect("slot_list", user_id=slot.expert_id)

            # ❌ DUPLICATE ACTIVE BOOKING
            if Booking.objects.filter(
                booked_by=request.user,
                slot__expert_id=slot.expert_id,
                is_cancelled=False,
                slot__end_time__gt=now
            ).exists():
                messages.error(request, "You already have an active booking with this expert.")
                return redirect("slot_list", user_id=slot.expert_id)

            # ✅ CREATE BOOKING
            booking = Booking.objects.create(
                slot=slot,
                booked_by=request.user
            )

            host = slot.expert
            user = request.user
            profile = host.profile
            mode = profile.availability_mode
            display_name = (
                f"{request.user.first_name} {request.user.last_name}".strip()
                if request.user.first_name or request.user.last_name
                else request.user.username
            )
            # =========================
            # 🔥 MODE DETAILS
            # =========================

            if mode == "remote":
                user_mode_block = f"""
🔗 Meeting Link:
{booking.meeting_link}

• Join 5 minutes early
• Ensure stable internet connection
"""

                expert_mode_block = f"""
🔗 Meeting Link:
{booking.meeting_link}

• Be ready 5 minutes before start
"""

            elif mode == "onsite":
                user_mode_block = """
📍 Onsite Session

• Contact the expert for exact location
• Arrive 5–10 minutes early
"""

                expert_mode_block = """
📍 Onsite Session

• Reach out to the user and discuss the exact meeting location.
• Be ready before the scheduled time
"""

            else:
                user_mode_block = """
📌 Session mode not yet determined

• The expert will contact you with details
"""

                expert_mode_block = """
📌 Session mode not yet determined

• Please confirm whether this will be remote or onsite
"""

            # =========================
            # 📧 USER EMAIL
            # =========================

            user_message = f"""Hello {display_name},

Your session has been successfully booked.

━━━━━━━━━━━━━━━━━━━━━━
👤 Expert Details
━━━━━━━━━━━━━━━━━━━━━━
User: {host.display_name}
Email: {host.email}

━━━━━━━━━━━━━━━━━━━━━━
📅 Session Details
━━━━━━━━━━━━━━━━━━━━━━
Expert: {host.display_name}
Date: {booking.slot.start_time.strftime('%B %d, %Y')}
Time: {booking.slot.start_time.strftime('%I:%M %p')} - {booking.slot.end_time.strftime('%I:%M %p')}
Mode: {mode.title()}

━━━━━━━━━━━━━━━━━━━━━━
📌 Instructions
━━━━━━━━━━━━━━━━━━━━━━
{user_mode_block}

━━━━━━━━━━━━━━━━━━━━━━
📎 Important Notes
━━━━━━━━━━━━━━━━━━━━━━
• You can cancel or manage your booking from your dashboard
• Contact the expert if anything is unclear
• Reach out to the expert and discuss the exact meeting location.

Best regards,  
The FancyLearn Team
"""

            # =========================
            # 📧 EXPERT EMAIL
            # =========================

            expert_message = f"""Hello {host.display_name},

You have received a new booking.

━━━━━━━━━━━━━━━━━━━━━━
👤 Client Details
━━━━━━━━━━━━━━━━━━━━━━
User: {display_name}
Email: {user.email}

━━━━━━━━━━━━━━━━━━━━━━
📅 Session Details
━━━━━━━━━━━━━━━━━━━━━━
Date: {booking.slot.start_time.strftime('%B %d, %Y')}
Time: {booking.slot.start_time.strftime('%I:%M %p')} - {booking.slot.end_time.strftime('%I:%M %p')}
Mode: {mode.title()}

━━━━━━━━━━━━━━━━━━━━━━
📌 Your Responsibilities
━━━━━━━━━━━━━━━━━━━━━━
{expert_mode_block}

━━━━━━━━━━━━━━━━━━━━━━
📎 Notes
━━━━━━━━━━━━━━━━━━━━━━
• Make sure to be prepared before the session
• Communicate clearly with the client if needed

Best regards,  
The FancyLearn Team
"""

            # =========================
            # 🔔 NOTIFICATIONS
            # =========================

            NotificationService.create_notification(
                users=[host],
                actor=user,
                message=f"New booking from {display_name}",
                url=reverse("slot_list", kwargs={"user_id": host.id})
            )

            NotificationService.create_notification(
                users=[user],
                actor=user,
                message=f"Booking confirmed with {display_name}",
                url=reverse("slot_list", kwargs={"user_id": host.id})
            )

            # =========================
            # 📤 SEND EMAILS SEPARATELY
            # =========================

            send_mail(
                subject="🎉 Your Booking is Confirmed",
                message=user_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )

            send_mail(
                subject="📅 New Booking Received",
                message=expert_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[host.email],
                fail_silently=False
            )

            messages.success(request, "Booking successful.")
            return redirect("slot_list", user_id=host.id)


# =====================================
# ❌ CANCEL BOOKING (SAFE)
# =====================================
@method_decorator(login_required, name="dispatch")
class BookingCancelView(LoginRequiredMixin, View):

    def post(self, request, booking_id):

        booking = get_object_or_404(
            Booking,
            id=booking_id,
            is_cancelled=False
        )

        user = request.user
        host = booking.slot.expert

        # ❌ unauthorized
        if user not in [booking.booked_by, host]:
            return HttpResponseForbidden()

        # 🔥 WHO CANCELLED
        cancelled_by_user = (user == booking.booked_by)
        cancelled_by = "client" if cancelled_by_user else "expert"

        with transaction.atomic():

            booking.cancel()

            # =========================
            # 📅 COMMON DETAILS
            # =========================

            session_date = booking.slot.start_time.strftime('%B %d, %Y')
            session_time = f"{booking.slot.start_time.strftime('%I:%M %p')} - {booking.slot.end_time.strftime('%I:%M %p')}"
            display_name = (
                f"{request.user.first_name} {request.user.last_name}".strip()
                if request.user.first_name or request.user.last_name
                else request.user.username
            )
            # =========================
            # 🔔 NOTIFICATIONS
            # =========================

            NotificationService.create_notification(
                users=[booking.booked_by, host],
                actor=user,
                message=(
                    f"Booking cancelled by {display_name} "
                    f"({cancelled_by}) • {session_date} {session_time}"
                ),
                url=reverse("slot_list", kwargs={"user_id": host.id})
            )

            # =========================
            # 📧 USER EMAIL
            # =========================

            user_message = f"""Hello {display_name},

Your booking has been cancelled.

━━━━━━━━━━━━━━━━━━━━━━
📅 Session Details
━━━━━━━━━━━━━━━━━━━━━━
Expert: {host.display_name}
Date: {session_date}
Time: {session_time}

━━━━━━━━━━━━━━━━━━━━━━
❌ Cancellation Info
━━━━━━━━━━━━━━━━━━━━━━
Cancelled by: {display_name} ({cancelled_by})

━━━━━━━━━━━━━━━━━━━━━━
📌 What Next?
━━━━━━━━━━━━━━━━━━━━━━
• You can book another available slot
• Contact the expert if needed

Best regards,  
The FancyLearn Team
"""

            # =========================
            # 📧 EXPERT EMAIL
            # =========================

            expert_message = f"""Hello {host.display_name},

A booking has been cancelled.

━━━━━━━━━━━━━━━━━━━━━━
👤 Client
━━━━━━━━━━━━━━━━━━━━━━
User: {display_name}

━━━━━━━━━━━━━━━━━━━━━━
📅 Session Details
━━━━━━━━━━━━━━━━━━━━━━
Date: {session_date}
Time: {session_time}

━━━━━━━━━━━━━━━━━━━━━━
❌ Cancellation Info
━━━━━━━━━━━━━━━━━━━━━━
Cancelled by: {display_name} ({cancelled_by})

━━━━━━━━━━━━━━━━━━━━━━
📌 Notes
━━━━━━━━━━━━━━━━━━━━━━
• This time slot is now available again
• You may update or keep the slot active

Best regards,  
The FancyLearn Team
"""

            # =========================
            # 📤 SEND EMAILS
            # =========================

            send_mail(
                subject="❌ Your Booking Was Cancelled",
                message=user_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.booked_by.email],
                fail_silently=True
            )

            send_mail(
                subject="📅 Booking Cancelled",
                message=expert_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[host.email],
                fail_silently=True
            )

        messages.success(request, "Booking cancelled successfully.")
        return redirect("slot_list", user_id=host.id)
    