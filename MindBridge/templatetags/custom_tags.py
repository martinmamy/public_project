
from django import template
from django.utils.safestring import mark_safe
from bs4 import BeautifulSoup
import re



register = template.Library()


@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Safely add CSS classes to Django form fields.
    Prevents crashing if field is already a string.
    """
    if hasattr(field, "as_widget"):
        existing_classes = field.field.widget.attrs.get("class", "")
        combined_classes = f"{existing_classes} {css_class}".strip()
        return field.as_widget(attrs={"class": combined_classes})

    # If it's already rendered as string, just return it
    return field

@register.filter(name='add_attrs')
def add_attrs(field, attrs):
    attr_dict = {}
    for attr in attrs.split(','):
        key, value = attr.split('=')
        attr_dict[key] = value
    return field.as_widget(attrs=attr_dict)

@register.filter
def truncate_html_chars(value, num):
    soup = BeautifulSoup(value, "html.parser")
    text = soup.get_text()
    if len(text) <= num:
        return value
    truncated_text = text[:num] + "…"
    return truncated_text


@register.filter
def smart_breaks(value):
    """
    Break long unpunctuated text into sentences or chunks for readability.
    """
    # Split by punctuation, else every 100 chars
    sentences = re.split(r'([.!?])', value)
    if len(sentences) > 1:
        result = "".join([s.strip() + " " for s in sentences if s.strip()])
    else:
        # Add artificial breaks every 120 characters if no punctuation
        result = " ".join([value[i:i+120] for i in range(0, len(value), 120)])
    return result


@register.filter
def problem_summary(value):
    """
    Extract the first full sentence from the problem text as a summary.
    """
    if not value:
        return ""
    # Remove HTML tags if any
    clean_text = re.sub(r'<[^>]+>', '', value)
    # Match first sentence ending with ., ! or ?
    match = re.search(r'(.+?[.!?])(\s|$)', clean_text)
    if match:
        return match.group(1)
    # fallback: first 120 chars
    return clean_text[:120] + "…"


URL_PATTERN = re.compile(
    r'(?<!["\'])\b(https?://[^\s<]+|www\.[^\s<]+)\b',
    re.IGNORECASE
)

@register.filter
def linkify(value):
    if not value:
        return value

    def replace(match):
        raw_url = match.group(0)

        # 🔥 BLOCK broken/encoded stuff (SVG, HTML entities, data URLs)
        if any(x in raw_url for x in ["%3C", "%3E", "svg", "data:", "base64"]):
            return raw_url

        # normalize URL
        href = raw_url if raw_url.startswith("http") else f"https://{raw_url}"

        return f'<a href="{href}" class="safe-link" target="_blank">{raw_url}</a>'

    return mark_safe(URL_PATTERN.sub(replace, value))


@register.inclusion_tag("components/user_presence.html")
def user_presence(user):
    return {"user": user}