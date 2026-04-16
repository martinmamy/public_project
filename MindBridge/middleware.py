import errno
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import redirect
from django.urls import resolve, Resolver404, reverse
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve, Resolver404


# =========================
# 1. HANDLE NON-EXISTING URLS
# =========================
from django.conf import settings
from django.shortcuts import redirect, reverse


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
    Strong CSP header for external integrations (Stripe, PayPal, etc.)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        response["Content-Security-Policy"] = (
            "default-src 'self'; "

            "connect-src 'self' "
            "https://studies-buddy.com "
            "wss://studies-buddy.com "
            "https://nominatim.openstreetmap.org "
            "https://va.tawk.to "
            "wss://*.tawk.to "
            "https://translate.google.com "
            "https://translate-pa.googleapis.com "
            "https://checkout.stripe.com "
            "https://hooks.stripe.com "
            "https://*.js.stripe.com "
            "https://www.paypal.com "
            "https://*.paypal.com; "

            "style-src 'self' 'unsafe-inline' "
            "https://cdnjs.cloudflare.com "
            "https://cdn.jsdelivr.net "
            "https://fonts.googleapis.com; "

            "font-src 'self' data: "
            "https://fonts.gstatic.com "
            "https://cdnjs.cloudflare.com; "

            "script-src 'self' 'unsafe-inline' "
            "https://code.jquery.com "
            "https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com "
            "https://js.stripe.com "
            "https://translate.google.com "
            "https://pagead2.googlesyndication.com "
            "https://cdn.tiny.cloud "
            "https://embed.tawk.to "
            "https://www.paypal.com "
            "https://*.paypal.com; "

            "img-src 'self' data: "
            "https://www.google.com "
            "https://fonts.gstatic.com "
            "https://translate.googleapis.com "
            "https://www.paypalobjects.com; "

            "frame-src 'self' "
            "https://js.stripe.com "
            "https://checkout.stripe.com "
            "https://embed.tawk.to "
            "https://www.youtube.com "
            "https://www.paypal.com "
            "https://*.paypal.com; "

            "object-src 'none'; "
            "media-src 'self';"
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