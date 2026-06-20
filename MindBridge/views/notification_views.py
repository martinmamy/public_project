# MindBridge/views/notification_views.py

import json
import logging
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from MindBridge.models import Notification, PushSubscription
from MindBridge.services.notification_service import NotificationService
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.views.generic import TemplateView

User = get_user_model()

from django.utils.dateparse import parse_datetime
from django.utils import timezone

@method_decorator(login_required, name="dispatch")
class NotificationsListView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):

        now = timezone.now()

        notifications = Notification.objects.filter(
            user=request.user
        ).order_by("-created_at")[:20]

        data = []

        for n in notifications:

            actor_info = None
            if n.actor:
                actor_info = {
                    "id": n.actor.id,
                    "username": n.actor.username,
                    "first_name": n.actor.first_name,
                    "last_name": n.actor.last_name,
                    "avatar_url": n.actor.avatar.url if n.actor.avatar and hasattr(n.actor.avatar, 'url') else None,
                    "profile_url": f"/users/{n.actor.id}/"
                }

            data.append({
                "id": n.id,
                "message": n.message,
                "url": n.url or "#",
                "is_read": n.is_read,

                # ✅ FIXED TIMEZONE (CRITICAL)
                "created_at": timezone.localtime(n.created_at).strftime("%Y-%m-%d %I:%M %p"),

                "actor": actor_info,

                # optional debug consistency
                "server_time": timezone.localtime(now).strftime("%Y-%m-%d %I:%M %p"),
            })

        return JsonResponse({"notifications": data})


@method_decorator(login_required, name="dispatch")
class NotificationsApiView(LoginRequiredMixin, View):
    PAGE_SIZE = 5

    def get(self, request, *args, **kwargs):

        now = timezone.now()

        cursor = request.GET.get("cursor")

        qs = Notification.objects.filter(
            user=request.user
        ).order_by("-created_at")

        if cursor:
            qs = qs.filter(created_at__lt=cursor)

        notifications = list(qs[:self.PAGE_SIZE])

        data = []

        for n in notifications:

            actor_info = None
            if n.actor:
                actor_info = {
                    "id": n.actor.id,
                    "username": n.actor.username,
                    "first_name": n.actor.first_name,
                    "last_name": n.actor.last_name,
                    "avatar_url": getattr(n.actor.avatar, 'url', None) if n.actor.avatar else None,
                    "profile_url": f"/users/{n.actor.id}/"
                }

            data.append({
                "id": n.id,
                "message": n.message,
                "url": n.url or "#",
                "is_read": n.is_read,

                # ✅ FIXED TIMEZONE OUTPUT
                "created_at": timezone.localtime(n.created_at).strftime("%Y-%m-%d %I:%M %p"),

                "actor": actor_info,

                "server_now": timezone.localtime(now).strftime("%Y-%m-%d %I:%M %p"),
            })

        next_cursor = (
            notifications[-1].created_at.isoformat()
            if len(notifications) == self.PAGE_SIZE else None
        )

        return JsonResponse({
            "notifications": data,
            "next_cursor": next_cursor
        })


@method_decorator(login_required, name="dispatch")
class NotificationsPageView(LoginRequiredMixin, TemplateView):
    template_name = "notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["notifications"] = Notification.objects.filter(
            user=self.request.user
        ).order_by("-created_at")

        return context
    

@method_decorator(login_required, name="dispatch")
class MarkReadView(LoginRequiredMixin, View):
    """Mark a single notification as read."""
    def post(self, request, notif_id, *args, **kwargs):
        try:
            notif = Notification.objects.get(id=notif_id, user=request.user)
            notif.is_read = True
            notif.save()
            return JsonResponse({"success": True})
        except Notification.DoesNotExist:
            return JsonResponse({"success": False, "error": "Notification not found"}, status=404)


@method_decorator(login_required, name="dispatch")
class MarkAllReadView(LoginRequiredMixin, View):
    """Mark all unread notifications as read."""
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({"success": True})


@method_decorator(login_required, name="dispatch")
class DeleteNotificationView(LoginRequiredMixin, View):
    """Delete a single notification."""
    def post(self, request, notif_id, *args, **kwargs):
        deleted, _ = Notification.objects.filter(id=notif_id, user=request.user).delete()
        if deleted:
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "error": "Notification not found"}, status=404)


@method_decorator(login_required, name="dispatch")
class SendNotificationView(LoginRequiredMixin, View):
    """Send a notification to one or multiple users, including the actor (request.user)."""
    def post(self, request, *args, **kwargs):
        data = request.POST
        message = data.get("message")
        url = data.get("url", "")
        user_id = data.get("user_id")
        user_ids = data.getlist("user_ids[]")

        if user_id:
            recipient = User.objects.filter(id=user_id).first()
            if recipient:
                NotificationService.create_notification(
                    user=recipient,
                    actor=request.user,
                    message=message,
                    url=url
                )
        elif user_ids:
            users = User.objects.filter(id__in=user_ids)
            NotificationService.create_notification(
                users=users,
                actor=request.user,
                message=message,
                url=url
            )
        else:
            return JsonResponse({"success": False, "error": "No user specified"}, status=400)

        return JsonResponse({"success": True})
    
    

from django.http import JsonResponse

logger = logging.getLogger(__name__)

@method_decorator(login_required, name="dispatch")
class SavePushSubscriptionView(View):

    def post(self, request):

        try:

            logger.info(f"🔔 PUSH SAVE REQUEST FROM: {request.user}")

            data = json.loads(request.body or "{}")

            # =========================================
            # FRONTEND SENDS DIRECT SUBSCRIPTION OBJECT
            # =========================================
            endpoint = data.get("endpoint")

            keys = data.get("keys", {})

            p256dh = keys.get("p256dh")
            auth = keys.get("auth")

            if not endpoint:
                return JsonResponse({
                    "success": False,
                    "error": "Missing endpoint"
                }, status=400)

            if not p256dh or not auth:
                return JsonResponse({
                    "success": False,
                    "error": "Missing keys"
                }, status=400)

            # =========================================
            # REMOVE DUPLICATES
            # =========================================
            PushSubscription.objects.filter(
                endpoint=endpoint
            ).delete()

            # =========================================
            # CREATE SUBSCRIPTION
            # =========================================
            subscription = PushSubscription.objects.create(

                user=request.user,

                endpoint=endpoint,

                p256dh=p256dh,

                auth=auth,

                browser=request.META.get(
                    "HTTP_USER_AGENT",
                    ""
                )
            )

            logger.info(
                f"✅ PUSH SUBSCRIPTION SAVED: {subscription.id}"
            )

            return JsonResponse({
                "success": True
            })

        except Exception as e:

            logger.exception("❌ PUSH SAVE ERROR")

            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)