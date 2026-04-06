# MindBridge/views/notification_views.py

from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from MindBridge.models import Notification
from MindBridge.services.notification_service import NotificationService
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required


User = get_user_model()

@method_decorator(login_required, name="dispatch")
class NotificationsListView(LoginRequiredMixin, View):
    """Return latest 20 notifications for the logged-in user, including actor info."""
    def get(self, request, *args, **kwargs):
        notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:20]

        data = []
        for n in notifications:
            actor_info = None
            if n.actor:
                actor_info = {
                    "id": n.actor.id,
                    "username": n.actor.username,
                    "avatar_url": n.actor.avatar.url if n.actor.avatar and hasattr(n.actor.avatar, 'url') else None,
                    "profile_url": f"/users/{n.actor.id}/"
                }

            data.append({
                "id": n.id,
                "message": n.message,
                "url": n.url or "#",
                "is_read": n.is_read,
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M"),
                "actor": actor_info
            })

        return JsonResponse({"notifications": data})


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