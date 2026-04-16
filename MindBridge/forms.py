from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
        
from MindBridge.models import (
    UserProfile, User, Problem, Answer,
    Comment, Vote, Follow, Tip, Bounty, CreatorSubscription,
    Notification, Report, Advertisement, Bookmark
)
from MindBridge.predefined import PREDEFINED_CATEGORIES

from MindBridge.models import UserProfile
from MindBridge.util.moderation import contains_bad_words

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
    website = forms.URLField(required=False, widget=forms.URLInput(attrs={"class": "form-control", "placeholder": "Website"}))
    profession = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Profession"}))
    country = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Country"}))

    class Meta:
        model = UserProfile
        fields = ["website", "profession", "country", "bio", "avatar"]

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user

        # Save User fields
        user.bio = self.cleaned_data.get("bio", user.bio)
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

class ProblemForm(forms.ModelForm):

    # Hidden input for JS dynamic tags
    tags_input = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Enter tags separated by commas."
    )

    # Post type field
    post_type = forms.ChoiceField(
        choices=Problem.POST_TYPE_CHOICES,
        initial="issue",
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Post Type",
        help_text="Select whether this post is an issue or information"
    )

    class Meta:
        model = Problem
        fields = ["title", "description", "category", "bounty_amount", "file", "post_type"]

        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Problem title"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 6, "placeholder": "Describe your problem"}
            ),
            "category": forms.Select(
                choices=PREDEFINED_CATEGORIES,
                attrs={"class": "form-select"}
            ),
            "bounty_amount": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 1}
            ),
            "file": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*,video/*,audio/*"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["bounty_amount"].required = False

        # preload tags when editing
        if self.instance and self.instance.tags:
            self.initial["tags_input"] = self.instance.tags

        # preload post type when editing
        if self.instance and self.instance.post_type:
            self.initial["post_type"] = self.instance.post_type

    # =========================================================
    # 🔥 BAD WORD VALIDATION (MAIN FIX)
    # =========================================================
    def clean(self):
        cleaned_data = super().clean()

        title = cleaned_data.get("title", "")
        description = cleaned_data.get("description", "")

        if contains_bad_words(title) or contains_bad_words(description):
            raise forms.ValidationError(
                "Your post contains inappropriate language."
            )

        return cleaned_data

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)

        if user:
            instance.author = user

        # tags handling
        tags_str = self.cleaned_data.get("tags_input", "")
        instance.tags = ",".join(
            [t.strip() for t in tags_str.split(",") if t.strip()]
        )

        # post type handling
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
class CreatorSubscriptionForm(forms.ModelForm):
    class Meta:
        model = CreatorSubscription
        fields = ["creator", "subscriber", "monthly_fee", "active"]
        widgets = {
            "creator": forms.Select(attrs={"class": "form-select"}),
            "subscriber": forms.Select(attrs={"class": "form-select"}),
            "monthly_fee": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

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