import errno
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import redirect
from django.urls import resolve, Resolver404, reverse
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve, Resolver404
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone


# =========================
# 1. HANDLE NON-EXISTING URLS
# =========================
from django.conf import settings
from django.shortcuts import redirect, reverse

from MindBridge.models import Advertisement


class RedirectNonExistingURLsMiddleware:
    """
    Handles 404 redirects differently for DEV and PROD.
    """

    EXCLUDED_PREFIXES = ()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Skip static/media/admin early
        if path.startswith(settings.STATIC_URL) or path.startswith(settings.MEDIA_URL) or path.startswith("/admin/"):
            return self.get_response(request)

        response = self.get_response(request)

        # Only handle real HTML 404 pages
        if response.status_code != 404:
            return response

        accept = request.headers.get("accept", "")

        # API requests should NEVER redirect
        if "text/html" not in accept:
            return response

        # DEV
        if settings.DEBUG:
            return redirect("missing_page_dev")

        # PROD
        return redirect("missing_page")


# =========================
# 2. ADMIN ACCESS CONTROL
# =========================
class AdminAccessMiddleware:
    """
    Prevent non-staff users from accessing Django admin.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith('/admin/'):
            user = request.user
            if not (user.is_authenticated and user.is_staff and user.is_superuser):
                return redirect(reverse('home'))

        return self.get_response(request)


# =========================
# 3. MAINTENANCE MODE
# =========================
class MaintenanceModeMiddleware:
    """
    Redirect all users to maintenance page except whitelisted IPs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if getattr(settings, 'MAINTENANCE_MODE', False):

            user_ip = request.META.get('REMOTE_ADDR')
            whitelist = getattr(settings, 'WHITELISTED_IPS', [])

            maintenance_url = reverse('maintenance_page')

            if user_ip not in whitelist and not request.path.startswith(maintenance_url):
                return HttpResponseRedirect(maintenance_url)

        return self.get_response(request)


# =========================
# 4. SECURITY HEADERS
# =========================
class SecureHeadersMiddleware(MiddlewareMixin):
    """
    Adds security headers to every response.
    """

    def process_response(self, request, response):

        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # SAFE removal of server header
        try:
            response.headers.pop('Server', None)
        except Exception:
            pass

        return response


# =========================
# 5. CONTENT SECURITY POLICY
# =========================
class ContentSecurityPolicyMiddleware:
    """
    Strong CSP header with proper CDN + source map handling
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        response["Content-Security-Policy"] = (

            "default-src 'self'; "

            # =========================
            # CONNECT (XHR / fetch / websockets)
            # =========================
            "connect-src 'self' "
            "https://nominatim.openstreetmap.org "
            "https://translate.google.com "
            "https://translate-pa.googleapis.com "
            "https://checkout.stripe.com "
            "https://hooks.stripe.com "
            "https://*.js.stripe.com "
            "https://www.paypal.com "
            "https://*.paypal.com "
            "https://cdn.jsdelivr.net; "

            # =========================
            # SCRIPTS
            # =========================
            "script-src 'self' 'unsafe-inline' "
            "https://code.jquery.com "
            "https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com "
            "https://cdn.quilljs.com "
            "https://js.stripe.com "
            "https://translate.google.com "
            "https://pagead2.googlesyndication.com "
            "https://cdn.tiny.cloud "
            "https://embed.tawk.to "
            "https://www.paypal.com "
            "https://*.paypal.com; "

            # =========================
            # STYLES
            # =========================
            "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com "
            "https://cdn.quilljs.com "
            "https://fonts.googleapis.com; "

            # =========================
            # FONTS
            # =========================
            "font-src 'self' data: "
            "https://fonts.gstatic.com "
            "https://cdnjs.cloudflare.com; "

            # =========================
            # IMAGES
            # =========================
            "img-src 'self' data: blob: "
            "https://www.google.com "
            "https://fonts.gstatic.com "
            "https://translate.googleapis.com "
            "https://www.paypalobjects.com; "

            # =========================
            # FRAMES
            # =========================
            "frame-src 'self' "
            "https://js.stripe.com "
            "https://checkout.stripe.com "
            "https://embed.tawk.to "
            "https://www.youtube.com "
            "https://www.paypal.com "
            "https://*.paypal.com; "

            # =========================
            # OTHER
            # =========================
            "object-src 'none'; "
            "media-src 'self' blob:; "
        )

        return response


# =========================
# 6. BROKEN PIPE HANDLING
# =========================
class IgnoreBrokenPipeMiddleware:
    """
    Prevent server crash when client disconnects mid-response.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        try:
            return self.get_response(request)

        except OSError as e:
            if e.errno == errno.EPIPE:
                return HttpResponseServerError("Client disconnected")
            raise
        


from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone

class RecurringAdsMiddleware:

    CACHE_KEY = "recurring_ads_check"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if not cache.get(self.CACHE_KEY):

            cache.set(self.CACHE_KEY, True, timeout=300)

            now = timezone.now()

            # =====================================================
            # EXPIRED ADS (FOR RENEWAL)
            # =====================================================
            expired_ads = Advertisement.objects.filter(
                is_recurring=True,
                stop_recurring=False,
                is_deleted=False,
                expires_at__isnull=False,
                recurring_every__isnull=False,
                expires_at__lte=now
            )

            for ad in expired_ads:

                # Extra protection against bad data
                if not ad.expires_at or not ad.recurring_every:
                    continue

                while ad.expires_at <= now:
                    ad.expires_at += timedelta(
                        days=ad.recurring_every
                    )

                ad.status = "active"
                ad.save(update_fields=["expires_at", "status"])

            # =====================================================
            # LAST DAY CHECK (24 HOURS BEFORE EXPIRY)
            # =====================================================
            last_day_ads = Advertisement.objects.filter(
                is_recurring=True,
                stop_recurring=False,
                is_deleted=False,
                status="active",
                expires_at__isnull=False,
                expires_at__gt=now,
                expires_at__lte=now + timedelta(hours=24)
            )

            last_day_ads.update(
                is_expiring_soon=True
            )

            # =====================================================
            # LAST MINUTE CHECK (30 MINUTES BEFORE EXPIRY)
            # =====================================================
            urgent_ads = Advertisement.objects.filter(
                is_recurring=True,
                stop_recurring=False,
                is_deleted=False,
                status="active",
                expires_at__isnull=False,
                expires_at__gt=now,
                expires_at__lte=now + timedelta(minutes=30)
            )

            urgent_ads.update(
                is_urgent_expiry=True
            )

            # =====================================================
            # RESET FLAGS FOR OTHER ADS
            # =====================================================
            Advertisement.objects.exclude(
                id__in=last_day_ads.values_list("id", flat=True)
            ).update(
                is_expiring_soon=False
            )

            Advertisement.objects.exclude(
                id__in=urgent_ads.values_list("id", flat=True)
            ).update(
                is_urgent_expiry=False
            )

        return self.get_response(request)