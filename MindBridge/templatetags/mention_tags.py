# templatetags/mention_tags.py
from django import template
import re
from MindBridge.models import User
from django.utils.safestring import mark_safe
from django.utils.html import escape
import urllib.parse

register = template.Library()

MENTION_PATTERN = r'@([\w-]+)'

@register.filter
def convert_mentions(text):
    """Replace @username with clickable link including avatar, slightly nudged downward."""
    if not text:
        return ""

    def replace(match):
        username = match.group(1)
        try:
            user = User.objects.get(username=username)

            # Avatar or SVG fallback
            if getattr(user, "avatar", None) and hasattr(user.avatar, "url") and user.avatar.url:
                avatar_url = user.avatar.url
            else:
                first_letter = escape(user.username[0].upper())
                svg = f"""
                <svg xmlns='http://www.w3.org/2000/svg' width='16' height='16'>
                  <rect width='16' height='16' fill='#dee2e6'/>
                  <text x='50%' y='50%' dominant-baseline='central' text-anchor='middle'
                        font-family='Arial, sans-serif' font-size='10' fill='#343a40'>{first_letter}</text>
                </svg>
                """
                avatar_url = "data:image/svg+xml," + urllib.parse.quote(svg)

            # Inline link with avatar and username nudged slightly downward
            return (
                f"<a href='/auth/profile/{user.id}/' "
                f"style='text-decoration:none;color:#007bff;display:inline-flex;align-items:center;gap:2px;font-size:14px;'>"
                f"<img src='{avatar_url}' "
                f"style='width:1.05em;height:1.05em;border-radius:50%;object-fit:cover;vertical-align:middle;transform:translateY(2.5px);' "
                f"alt='{user.username}'>"
                f"<strong style='display:inline-block; transform:translateY(3.5px);'>{user.username}</strong>"
                f"</a>"
            )
        except User.DoesNotExist:
            return f"{escape(username)}"

    converted = re.sub(MENTION_PATTERN, replace, text)
    return mark_safe(converted)


@register.filter
def abbreviate_number(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return str(value)