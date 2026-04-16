# MindBridge/services/notification_service.py

from MindBridge.models import Notification

class NotificationService:
    @staticmethod
    def create_notification(user=None, users=None, message=None, url=None, actor=None):
        """
        Generic notification creator.
        Supports:
        - Single user
        - Multiple users
        - Optional actor (who triggered the notification)
        """
        if not message:
            raise ValueError("Notification message cannot be empty.")

        recipients = []

        # Single user
        if user:
            recipients.append(user)

        # Multiple users
        if users:
            recipients.extend(users)

        notifications = []
        for u in recipients:
            notifications.append(Notification(
                user=u,
                actor=actor,  # now saved correctly
                message=message,
                url=url or ""
            ))

        if notifications:
            Notification.objects.bulk_create(notifications) if len(notifications) > 1 else notifications[0].save()

        return notifications if len(notifications) > 1 else notifications[0]

    @staticmethod
    def notify_users(users, message, url=None, actor=None):
        """
        Helper wrapper for sending notifications to multiple users.
        """
        return NotificationService.create_notification(
            users=users,
            message=message,
            url=url,
            actor=actor
        )