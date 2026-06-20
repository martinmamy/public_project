from urllib.parse import urlparse
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError


# -----------------------------
# STRICT ALLOWED DOMAINS
# -----------------------------
ALLOWED_DOMAINS = {
    "zoom.us",
    "meet.google.com",
    "teams.microsoft.com",
    "teams.live.com",
    "webex.com",
    "webex.me",
    "cisco.com"   # Webex sometimes routes through Cisco domains
}


# -----------------------------
# SAFE URL VALIDATOR
# -----------------------------
def validate_safe_meeting_url(value):
    if not value:
        return

    value = value.strip()

    # 1. Basic Django validation
    try:
        URLValidator()(value)
    except ValidationError:
        raise ValidationError("Invalid URL format.")

    # 2. Parse URL
    parsed = urlparse(value)

    # 3. Must be HTTPS
    if parsed.scheme != "https":
        raise ValidationError("Only HTTPS URLs are allowed.")

    # 4. Must have hostname
    if not parsed.hostname:
        raise ValidationError("Invalid URL host.")

    domain = parsed.hostname.lower()

    # 5. Normalize www
    if domain.startswith("www."):
        domain = domain[4:]

    # 6. STRICT domain validation (safe match only)
    if domain not in ALLOWED_DOMAINS:
        raise ValidationError(
            "Only Zoom, Google Meet, Teams, or Webex links are allowed."
        )

    # 7. Block dangerous payload patterns
    dangerous_patterns = [
        "javascript:",
        "data:",
        "vbscript:",
        "<script",
        "%00",
        "@",
        "eval(",
        "document.cookie"
    ]

    lower_value = value.lower()
    if any(p in lower_value for p in dangerous_patterns):
        raise ValidationError("Unsafe URL content detected.")

    # 8. URL length limit
    if len(value) > 500:
        raise ValidationError("URL is too long.")