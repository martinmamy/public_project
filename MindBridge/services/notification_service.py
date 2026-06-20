import json
import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings

from pywebpush import (
    webpush,
    WebPushException
)

from MindBridge.models import (
    Notification,
    PushSubscription
)

logger = logging.getLogger(__name__)


# =========================================================
# THREAD POOL
# =========================================================
# Prevent push notifications from blocking requests
executor = ThreadPoolExecutor(max_workers=10)


# =========================================================
# SINGLE PUSH SENDER
# =========================================================
def _send_single_push(subscription, payload):

    try:

        logger.info(
            f"➡️ Sending push to subscription "
            f"{subscription.id}"
        )

        webpush(

            subscription_info={

                "endpoint": subscription.endpoint,

                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth
                }
            },

            data=json.dumps(payload),

            vapid_private_key=(
                settings.WEBPUSH_SETTINGS[
                    "VAPID_PRIVATE_KEY"
                ]
            ),

            vapid_claims={
                "sub": settings.WEBPUSH_SETTINGS[
                    "VAPID_ADMIN_EMAIL"
                ]
            },

            ttl=60 * 60 * 24
        )

        logger.info(
            f"✅ Push sent successfully "
            f"to subscription {subscription.id}"
        )

    except WebPushException as e:

        logger.error(
            f"❌ WebPush failed for "
            f"subscription {subscription.id}: "
            f"{repr(e)}"
        )

        response = getattr(e, "response", None)

        # =========================================
        # REMOVE INVALID SUBSCRIPTIONS
        # =========================================
        if response and response.status_code in [404, 410]:

            logger.warning(
                f"🗑 Removing expired "
                f"subscription {subscription.id}"
            )

            subscription.delete()

    except Exception as e:

        logger.exception(
            f"❌ Unexpected push error "
            f"for subscription "
            f"{subscription.id}: {str(e)}"
        )


# =========================================================
# ASYNC PUSH SENDER
# =========================================================
def send_push(user, payload):

    try:

        subscriptions = list(

            PushSubscription.objects.filter(
                user=user
            )
        )

        if not subscriptions:

            logger.warning(
                f"⚠️ No push subscriptions "
                f"for user: {user}"
            )

            return

        logger.info(
            f"🔔 Sending push to "
            f"{len(subscriptions)} devices "
            f"for {user}"
        )

        # =========================================
        # SEND PUSHES IN BACKGROUND THREADS
        # =========================================
        for subscription in subscriptions:

            executor.submit(
                _send_single_push,
                subscription,
                payload
            )

    except Exception as e:

        logger.exception(
            f"❌ Failed preparing push "
            f"notifications: {str(e)}"
        )


# =========================================================
# NOTIFICATION SERVICE
# =========================================================
class NotificationService:

    @staticmethod
    def create_notification(

        user=None,
        users=None,

        message=None,

        url=None,

        actor=None,

        send_push_notification=True
    ):

        # =========================================
        # VALIDATION
        # =========================================
        if not message:

            raise ValueError(
                "Notification message cannot be empty"
            )

        recipients = []

        if user:
            recipients.append(user)

        if users:
            recipients.extend(users)

        # =========================================
        # REMOVE DUPLICATES SAFELY
        # =========================================
        recipients = list({
            recipient.id: recipient
            for recipient in recipients
        }.values())

        if not recipients:

            logger.warning(
                "⚠️ No recipients provided"
            )

            return None

        notifications = []

        # =========================================
        # ACTOR INFO
        # =========================================
        if actor:

            full_name = (
                f"{actor.first_name or ''} "
                f"{actor.last_name or ''}"
            ).strip()

            actor_name = (
                full_name
                if full_name
                else actor.username
            )

        else:

            actor_name = "FancyLearn"

        actor_icon = (
            actor.avatar.url
            if (
                actor and
                getattr(actor, "avatar", None)
            )
            else "/static/images/default-avatar.png"
        )

        # =========================================
        # CREATE NOTIFICATIONS
        # =========================================
        for recipient in recipients:

            try:

                # =============================
                # CREATE IN-APP NOTIFICATION
                # =============================
                notification = Notification.objects.create(

                    user=recipient,

                    actor=actor,

                    message=message,

                    url=url or "/"
                )

                notifications.append(notification)

                logger.info(
                    f"✅ Notification created "
                    f"for user {recipient}"
                )

                # =============================
                # PUSH PAYLOAD
                # =============================
                payload = {

                    "title": actor_name,

                    "body": message,

                    "url": url or "/",

                    "tag": (
                        f"notif-"
                        f"{notification.id}"
                    ),

                    "icon": actor_icon,

                    "badge":
                        "/static/images/default-avatar.png",

                    "data": {

                        "notification_id":
                            notification.id
                    }
                }

                # =============================
                # SEND PUSH ASYNC
                # =============================
                if send_push_notification:

                    send_push(
                        recipient,
                        payload
                    )

            except Exception as e:

                logger.exception(
                    f"❌ Failed creating "
                    f"notification for "
                    f"{recipient}: {str(e)}"
                )

        # =========================================
        # RETURN
        # =========================================
        if not notifications:

            return None

        return (
            notifications[0]
            if len(notifications) == 1
            else notifications
        )

    @staticmethod
    def notify_users(
        users,
        message,
        url=None,
        actor=None
    ):

        return NotificationService.create_notification(

            users=users,

            message=message,

            url=url,

            actor=actor
        )