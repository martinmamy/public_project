from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db.models.functions import FirstValue
        
from MindBridge.models import (
    UserProfile, User, Problem, Answer,
    Comment, Vote, Follow, Tip, Bounty, CreatorsSubscription,
    Notification, Report, Advertisement, Bookmark
)
from MindBridge.predefined import PREDEFINED_CATEGORIES

from MindBridge.models import UserProfile
from MindBridge.util.moderation import contains_bad_words
from MindBridge.validators import validate_safe_meeting_url

User = get_user_model()


# ----------------------------------
# REGISTER FORM
# ----------------------------------
class RegisterForm(UserCreationForm):

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Username"
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Email"
        })
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password"
        })
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm Password"
        })
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


# ----------------------------------
# LOGIN FORM
# ----------------------------------
class LoginForm(forms.Form):

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Username"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password"
        })
    )


# ----------------------------------
# Update Profile Form
# ----------------------------------
class UpdateProfileForm(forms.ModelForm):
    # Fields from User model
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Write a short bio..."})
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"})
    )

    # Fields from UserProfile
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}))
    website = forms.URLField(required=False, widget=forms.URLInput(attrs={"class": "form-control", "placeholder": "Website"}))
    profession = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Profession"}))
    country = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Country"}))

    class Meta:
        model = UserProfile
        fields = ["website", "profession", "country", "bio", "avatar", "first_name", "last_name"]

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user

        # Save User fields
        user.bio = self.cleaned_data.get("bio", user.bio)
        user.first_name = self.cleaned_data.get("first_name", user.first_name)
        user.last_name = self.cleaned_data.get("last_name", user.last_name)
        avatar = self.cleaned_data.get("avatar")
        if avatar:
            user.avatar = avatar

        if commit:
            user.save()
            profile.save()
        return profile

# =========================================================
# 1. User Profile Form
# =========================================================
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["website", "country", "profession"]
        widgets = {
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "profession": forms.TextInput(attrs={"class": "form-control"}),
        }


# =========================================================
# 4. Problem Form
# =========================================================
from django.core.validators import MinValueValidator

from django import forms


import re
from django.core.exceptions import ValidationError

import re
import bleach
from django import forms
from django.core.exceptions import ValidationError

URL_REGEX = re.compile(
    r"(https?://\S+|www\.\S+|\b[a-z0-9-]+\.(com|net|org|io|me|us|xyz)\b)",
    re.IGNORECASE
)

def contains_url(text):
    return bool(URL_REGEX.search(text or ""))


import bleach
from django import forms
from django.core.exceptions import ValidationError

class ProblemForm(forms.ModelForm):

    tags_input = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Enter tags separated by commas."
    )

    post_type = forms.ChoiceField(
        choices=Problem.POST_TYPE_CHOICES,
        initial="issue",
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Post Type"
    )

    class Meta:
        model = Problem
        fields = [
            "title",
            "description",
            "category",
            "bounty_amount",
            "file",
            "post_type"
        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Problem title"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": "Describe your problem"
            }),
            "category": forms.Select(attrs={
                "class": "form-select"
            }),
            "bounty_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
                "step": 1
            }),
            "file": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/*,video/*,audio/*"
            }),
        }

    # =========================================================
    # 🔥 TITLE VALIDATION (STRICT)
    # =========================================================
    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()

        if contains_url(title):
            raise ValidationError("Links are not allowed in the title.")

        if contains_bad_words(title):
            raise ValidationError("Inappropriate content in title.")

        if len(title) < 5:
            raise ValidationError("Title is too short.")

        return title

    # =========================================================
    # 🔥 DESCRIPTION (SAFE HTML SANITIZATION)
    # =========================================================
    def clean_description(self):
        description = self.cleaned_data.get("description") or ""

        if contains_bad_words(description):
            raise ValidationError("Your post contains inappropriate language.")

        allowed_tags = [
            "b", "i", "u", "strong", "em",
            "p", "br",
            "ul", "ol", "li",
            "code", "pre",
            "a"
        ]

        allowed_attrs = {
            "a": ["href", "target", "rel"]
        }

        cleaned = bleach.clean(
            description,
            tags=allowed_tags,
            attributes=allowed_attrs,
            protocols=["http", "https", "mailto"],
            strip=True
        )

        return cleaned

    # =========================================================
    # 🔥 CROSS FIELD VALIDATION
    # =========================================================
    def clean(self):
        cleaned_data = super().clean()

        bounty = cleaned_data.get("bounty_amount") or 0
        post_type = cleaned_data.get("post_type")

        # Example rule: no bounty on discussion posts
        if post_type == "discussion" and bounty > 0:
            raise ValidationError("Discussions cannot have bounties.")

        return cleaned_data

    # =========================================================
    # 🔥 SAFE SAVE LOGIC
    # =========================================================
    def save(self, commit=True, user=None):
        instance = super().save(commit=False)

        if user:
            instance.author = user

        # -------------------------
        # TAG CLEANING (IMPROVED)
        # -------------------------
        tags_str = self.cleaned_data.get("tags_input", "")

        clean_tags = [
            t.strip().lower()
            for t in tags_str.split(",")
            if t.strip()
        ]

        # remove duplicates
        instance.tags = ",".join(sorted(set(clean_tags)))

        # -------------------------
        # POST TYPE
        # -------------------------
        instance.post_type = self.cleaned_data.get("post_type", "issue")

        if commit:
            instance.save()

        return instance

# =========================================================
# ANSWER FORM WITH OPTIONAL MEDIA
# =========================================================

from django import forms

class AnswerForm(forms.ModelForm):

    class Meta:
        model = Answer
        fields = ["content", "file"]

        widgets = {
            "content": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".jpg,.jpeg,.png,.gif,.mp4,.mov,.avi,.mkv,.webm,.mp3,.wav,.aac",
                }
            ),
        }

        labels = {
            "content": "Answer",
            "file": "Attach Media (optional)",
        }

        help_texts = {
            "content": "Provide a clear, detailed answer to the problem.",
            "file": "Optional media upload: image, video, or audio. Max size 20MB, max duration 5 min.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].required = False

    # =========================================================
    # 🔥 BAD WORD VALIDATION
    # =========================================================
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content", "")

        if contains_bad_words(content):
            raise forms.ValidationError(
                "Your answer contains inappropriate language."
            )

        return cleaned_data

# =========================================================
# 7. Comment Form
# =========================================================
from django import forms
from .models import Comment

class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ["content"]

        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Write your comment...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ REMOVE "Content:" LABEL COMPLETELY
        self.fields["content"].label = ""
        self.fields["content"].label_suffix = ""

    # =========================================================
    # 🔥 BAD WORD VALIDATION
    # =========================================================
    def clean_content(self):
        content = self.cleaned_data.get("content", "")

        if contains_bad_words(content):
            raise forms.ValidationError(
                "Your comment contains inappropriate language."
            )

        return content
    
# =========================================================
# 8. Vote Form
# =========================================================
class VoteForm(forms.ModelForm):
    class Meta:
        model = Vote
        fields = ["problem", "answer", "value"]
        widgets = {
            "problem": forms.Select(attrs={"class": "form-select"}),
            "answer": forms.Select(attrs={"class": "form-select"}),
            "value": forms.NumberInput(attrs={"class": "form-control", "min": -1, "max": 1}),
        }

# =========================================================
# 9. Follow Form
# =========================================================
class FollowForm(forms.ModelForm):
    class Meta:
        model = Follow
        fields = ["follower", "following"]
        widgets = {
            "follower": forms.Select(attrs={"class": "form-select"}),
            "following": forms.Select(attrs={"class": "form-select"}),
        }

# =========================================================
# 10. Tip Form
# =========================================================
class TipForm(forms.ModelForm):
    class Meta:
        model = Tip
        fields = ["sender", "receiver", "answer", "amount"]
        widgets = {
            "sender": forms.Select(attrs={"class": "form-select"}),
            "receiver": forms.Select(attrs={"class": "form-select"}),
            "answer": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }

# =========================================================
# 11. Bounty Form
# =========================================================
class BountyForm(forms.ModelForm):
    class Meta:
        model = Bounty
        fields = ["problem", "creator", "amount", "expires_at", "awarded_to"]
        widgets = {
            "problem": forms.Select(attrs={"class": "form-select"}),
            "creator": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "expires_at": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "awarded_to": forms.Select(attrs={"class": "form-select"}),
        }

# =========================================================
# 12. Creator Subscription Form
# =========================================================
from django import forms

from MindBridge.models import CreatorsSubscription


# =========================================================
# SUBSCRIPTION FORM (CREATE / UPDATE)
# =========================================================

class CreatorsSubscriptionForm(forms.ModelForm):

    class Meta:

        model = CreatorsSubscription

        fields = (
            "user",
            "plan",
            "amount",
            "status",
            "active",
            "premium_access",
            "paypal_subscription_id",
            "paypal_plan_id",
            "started_at",
            "next_billing_time",
            "cancelled_at",
            "expired_at",
        )

        widgets = {

            "user": forms.Select(attrs={
                "class": "form-control"
            }),

            "plan": forms.Select(attrs={
                "class": "form-control"
            }),

            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01"
            }),

            "status": forms.Select(attrs={
                "class": "form-control"
            }),

            "active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),

            "premium_access": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),

            "paypal_subscription_id": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "paypal_plan_id": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "started_at": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),

            "next_billing_time": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),

            "cancelled_at": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),

            "expired_at": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),
        }

    # =========================================================
    # VALIDATION RULES
    # =========================================================

    def clean(self):

        cleaned_data = super().clean()

        plan = cleaned_data.get("plan")
        amount = cleaned_data.get("amount")
        active = cleaned_data.get("active")

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if plan == CreatorsSubscription.Plan.MONTHLY:

            if amount and amount <= 0:

                raise forms.ValidationError(
                    "Monthly plan must have a valid amount."
                )

        if plan == CreatorsSubscription.Plan.YEARLY:

            if amount and amount <= 0:

                raise forms.ValidationError(
                    "Yearly plan must have a valid amount."
                )

        # -------------------------------------------------
        # BUSINESS RULE
        # -------------------------------------------------

        if active and cleaned_data.get("status") != CreatorsSubscription.Status.ACTIVE:

            raise forms.ValidationError(
                "Active subscription must have ACTIVE status."
            )

        return cleaned_data
# =========================================================
# 13. Notification Form
# =========================================================
class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ["user", "message", "url", "is_read"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "url": forms.URLInput(attrs={"class": "form-control"}),
            "is_read": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

# =========================================================
# 14. Report Form
# =========================================================
class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["reporter", "problem", "answer", "reason", "status"]
        widgets = {
            "reporter": forms.Select(attrs={"class": "form-select"}),
            "problem": forms.Select(attrs={"class": "form-select"}),
            "answer": forms.Select(attrs={"class": "form-select"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }



# =========================================================
# 16. Bookmark Form
# =========================================================
class BookmarkForm(forms.ModelForm):
    class Meta:
        model = Bookmark
        fields = ["user", "problem"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "problem": forms.Select(attrs={"class": "form-select"}),
        }
        

from .models import EventHub


class EventHubForm(forms.ModelForm):

    class Meta:
        model = EventHub
        fields = [
            "category",
            "title",
            "description",
            "start_time",
            "end_time",
            "meeting_url",
        ]

        widgets = {
            "category": forms.Select(attrs={
                "class": "form-control"
            }),
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Event title"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe your event..."
            }),
            "start_time": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-control"
            }),
            "end_time": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-control"
            }),
            "meeting_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://meet link (optional)"
            }),
        }

    # ✅ THIS MUST BE OUTSIDE Meta
    def clean_meeting_url(self):
        url = self.cleaned_data.get("meeting_url")

        if not url:
            return ""

        validate_safe_meeting_url(url)
        return url
    

from django import forms
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class AdminSendEmailForm(forms.Form):

    # =========================
    # RECIPIENT (FIXED)
    # =========================
    # Now supports MULTIPLE emails via JS (comma-separated)
    recipient = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    subject = forms.CharField(
        label="Email Subject",
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter email subject"
        })
    )

    body = forms.CharField(
        required=False,  # handled by Quill
        widget=forms.HiddenInput()
    )

    send_to_all = forms.BooleanField(
        required=False,
        label="Send to all users",
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input"
        })
    )

    # =========================
    # BODY VALIDATION
    # =========================
    def clean_body(self):
        body = self.cleaned_data.get("body", "").strip()

        # Quill empty states
        if body in ["", "<p><br></p>"]:
            raise ValidationError("Email body cannot be empty.")

        return body

    # =========================
    # MAIN VALIDATION (FIXED)
    # =========================
    def clean(self):
        cleaned_data = super().clean()

        recipient_raw = cleaned_data.get("recipient")
        send_to_all = cleaned_data.get("send_to_all")

        # If send_to_all is checked → ignore recipients completely
        if send_to_all:
            cleaned_data["recipient"] = ""
            return cleaned_data

        # Must have at least something
        if not recipient_raw:
            raise ValidationError(
                "Provide at least one recipient or select 'Send to all users'."
            )

        # =========================
        # PARSE MULTIPLE EMAILS
        # =========================
        emails = [
            email.strip().lower()
            for email in recipient_raw.split(",")
            if email.strip()
        ]

        if not emails:
            raise ValidationError("No valid recipients found.")

        # =========================
        # VALIDATE EACH EMAIL
        # =========================
        invalid_emails = []

        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                invalid_emails.append(email)

        if invalid_emails:
            raise ValidationError(
                f"Invalid email(s): {', '.join(invalid_emails[:5])}"
            )

        # Save cleaned version back as CSV
        cleaned_data["recipient"] = ",".join(emails)

        return cleaned_data