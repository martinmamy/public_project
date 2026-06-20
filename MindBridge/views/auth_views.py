from datetime import timedelta
import json
from django.contrib import messages
from django.template.loader import render_to_string
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import UpdateView
from django.views.generic.list import ListView
from MindBridge.middleware import settings
from MindBridge.views.comment_views import LoginRequiredMixin
from MindBridge.views.data_processing import TemplateView
from MindBridge.views.events_views import UserPassesTestMixin
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from MindBridge.forms import RegisterForm, LoginForm, UpdateProfileForm
from MindBridge.models import AvailabilitySlot, UserProfile, Problem, EmailOTP, Answer, UserReport, Tip, Follow, User
from django.db.models import Sum
from MindBridge.services.expert_verification_service import ExpertVerificationService
from MindBridge.services.reputation_service import ReputationService
import random

from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.mail import EmailMessage
from django.conf import settings
from uuid import UUID
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags



User = get_user_model()


# =========================
# OTP GENERATOR (REUSED)
# =========================
def generate_and_send_otp(user, request):
    code = str(random.randint(100000, 999999))

    # 🔥 delete ALL previous OTPs
    EmailOTP.objects.filter(user=user).delete()

    EmailOTP.objects.create(
        user=user,
        code=make_password(code),
        expires_at=timezone.now() + timezone.timedelta(minutes=5)
    )

    send_mail(
        "Your Verification Code",
        f"Your code is: {code}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

    request.session["otp_attempts"] = 0


# =========================
# OTP GENERATOR (EMAIL ONLY)
# =========================
def generate_and_send_otp_email_only(email, request):
    code = str(random.randint(100000, 999999))

    request.session["email_otp"] = make_password(code)

    # store expiry timestamp
    request.session["email_otp_expires"] = (
        timezone.now() + timedelta(minutes=5)
    ).isoformat()

    request.session["otp_attempts"] = 0

    send_mail(
        "Verify your email",
        f"Your verification code is: {code}",
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    

MAX_ATTEMPTS = 3


# =========================
# REGISTER VIEW
# =========================
class RegisterView(View):
    template_name = "register.html"

    def get(self, request):
        return render(request, self.template_name, {"form": RegisterForm()})

    def post(self, request):
        try:
            data = json.loads(request.body)
            form = RegisterForm(data)
        except Exception:
            form = RegisterForm(request.POST)

        if form.is_valid():
            # DO NOT CREATE USER YET
            request.session["pending_user"] = {
                "username": form.cleaned_data["username"],
                "email": form.cleaned_data["email"],
                "password": form.cleaned_data["password1"],
            }

            generate_and_send_otp_email_only(
                form.cleaned_data["email"],
                request
            )

            return redirect("verify_email")

        return render(request, self.template_name, {"form": form})


from django.contrib.auth.hashers import check_password



def verify_user_otp(user, code):



    otp = (

        EmailOTP.objects

        .filter(user=user)

        .order_by("-created_at")

        .first()

    )



    if not otp:

        return False



    if otp.is_expired():

        otp.delete()

        return False



    if check_password(code, otp.code):

        otp.delete()  # single-use

        return True



    return False

# =====================================

# FORGOT PASSWORD

# =====================================



class ForgotPasswordView(View):



    template_name = "forgot_password.html"



    def get(self, request):

        return render(request, self.template_name)



    def post(self, request):



        email = request.POST.get("email", "").strip()



        try:

            user = User.objects.get(email=email)



        except User.DoesNotExist:



            messages.error(

                request,

                "No account found with this email."

            )



            return render(request, self.template_name)



        # reset session state

        request.session["otp_user_id"] = user.id

        request.session["otp_attempts"] = 0

        request.session["otp_type"] = "password_reset"



        # use same OTP system as login

        generate_and_send_otp(user, request)



        request.session.save()



        return redirect("verify_password_reset_otp")

# =====================================

# VERIFY PASSWORD RESET OTP

# =====================================



MAX_ATTEMPTS = 3



class VerifyPasswordResetOTPView(View):



    template_name = "verify_password_reset_otp.html"



    def get(self, request):



        if not request.session.get("otp_user_id"):

            return redirect("forgot_password")



        return render(request, self.template_name)



    def post(self, request):



        user_id = request.session.get("otp_user_id")



        if not user_id:

            return redirect("forgot_password")



        attempts = request.session.get("otp_attempts", 0)



        if attempts >= MAX_ATTEMPTS:



            request.session.flush()



            messages.error(

                request,

                "Too many failed attempts."

            )



            return redirect("forgot_password")



        code = request.POST.get("otp", "").strip()



        if not code:



            return render(request, self.template_name, {

                "error": "Please enter the OTP code."

            })



        try:

            user = User.objects.get(pk=user_id)



        except User.DoesNotExist:



            request.session.flush()



            return redirect("forgot_password")



        if verify_user_otp(user, code):



            request.session["password_reset_verified"] = True



            return redirect("reset_password")



        attempts += 1



        request.session["otp_attempts"] = attempts



        return render(request, self.template_name, {

            "error": (

                f"Invalid code. "

                f"Attempts left: {MAX_ATTEMPTS - attempts}"

            )

        })

# =====================================

# RESET PASSWORD

# =====================================



class ResetPasswordView(View):



    template_name = "reset_password.html"



    def get(self, request):



        if not request.session.get(

            "password_reset_verified"

        ):

            return redirect("forgot_password")



        return render(request, self.template_name)



    def post(self, request):



        if not request.session.get(

            "password_reset_verified"

        ):

            return redirect("forgot_password")



        password1 = request.POST.get("password1")

        password2 = request.POST.get("password2")



        if password1 != password2:



            messages.error(

                request,

                "Passwords do not match."

            )



            return render(request, self.template_name)



        user_id = request.session.get("otp_user_id")



        if not user_id:

            return redirect("forgot_password")



        try:

            user = User.objects.get(pk=user_id)



        except User.DoesNotExist:



            request.session.flush()



            return redirect("forgot_password")



        user.set_password(password1)

        user.save()



        # cleanup

        request.session.pop("otp_user_id", None)

        request.session.pop("otp_attempts", None)

        request.session.pop("otp_type", None)

        request.session.pop(

            "password_reset_verified",

            None

        )



        messages.success(

            request,

            "Password successfully reset. Please login."

        )



        return redirect("login")
    
    
# =========================
# VERIFY EMAIL VIEW
# =========================
class VerifyEmailView(View):
    template_name = "verify_email.html"

    def get(self, request):
        if not request.session.get("pending_user"):
            return redirect("register")

        return render(request, self.template_name)

    def post(self, request):
        pending = request.session.get("pending_user")

        if not pending:
            return redirect("register")

        code = request.POST.get("code")
        stored_otp = request.session.get("email_otp")

        attempts = request.session.get("otp_attempts", 0)

        # block brute force
        if attempts >= MAX_ATTEMPTS:
            request.session.flush()
            return render(request, self.template_name, {
                "error": "Too many failed attempts. Please register again."
            })

        # =========================
        # SUCCESS OTP
        # =========================
        if stored_otp and check_password(code, stored_otp):

            # NOW create user ONLY here
            user = User.objects.create_user(
                username=pending["username"],
                email=pending["email"],
                password=pending["password"],
                is_active=True  # user must verify email first
            )

            UserProfile.objects.create(user=user)

            # cleanup
            request.session.pop("pending_user", None)
            request.session.pop("email_otp", None)
            request.session.pop("otp_attempts", None)

            return redirect("login")

        # =========================
        # FAILED OTP
        # =========================
        request.session["otp_attempts"] = attempts + 1

        return render(request, self.template_name, {
            "error": f"Invalid code. Attempts left: {MAX_ATTEMPTS - (attempts + 1)}"
        })


# =========================
# LOGIN VIEW (OTP LOGIN)
# =========================
class LoginView(View):
    template_name = "login.html"

    def get(self, request):
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        try:
            data = json.loads(request.body)
            form = LoginForm(data)
        except Exception:
            form = LoginForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]

        User = get_user_model()

        try:
            user_obj = User.objects.get(username__iexact=username)
            username = user_obj.username
        except User.DoesNotExist:
            user_obj = None

        user = authenticate(request, username=username, password=password)

        if not user:
            form.add_error(None, "Invalid username or password")
            return render(request, self.template_name, {"form": form})

        if not user.is_active:
            form.add_error(None, "Account not verified. Check your email.")
            return render(request, self.template_name, {"form": form})

        # 🔥 RESET OTP STATE (IMPORTANT FIX)
        request.session["otp_user_id"] = str(user.pk)
        request.session["otp_attempts"] = 0
        request.session.modified = True

        # 🔥 GENERATE NEW OTP (OLD ONE IS DELETED IN FUNCTION)
        generate_and_send_otp(user, request)

        # 🔥 FORCE SESSION SAVE BEFORE REDIRECT
        request.session.save()

        if request.content_type == "application/json":
            return JsonResponse({"status": "otp_sent"})

        return redirect("verify_otp")

# =========================
# OTP LOGIN VERIFY VIEW
# =========================
MAX_ATTEMPTS = 3

from django.utils import timezone
from django.db import transaction

class VerifyOTPView(View):
    template_name = "verify_otp.html"

    def get(self, request):

        if not request.session.get("otp_user_id"):
            return redirect("login")

        return render(request, self.template_name)

    def post(self, request):

        user_id = request.session.get("otp_user_id")

        if not user_id:
            return redirect("login")

        attempts = request.session.get("otp_attempts", 0)

        # Too many attempts
        if attempts >= MAX_ATTEMPTS:

            request.session.flush()

            return render(request, self.template_name, {
                "error": "Too many failed attempts. Please login again."
            })

        code = request.POST.get("code", "").strip()

        if not code:
            return render(request, self.template_name, {
                "error": "Please enter the OTP code."
            })

        # Get user safely
        try:
            user = User.objects.get(pk=user_id)

        except User.DoesNotExist:

            request.session.flush()

            return redirect("login")

        # Get latest OTP
        otp = (
            EmailOTP.objects
            .filter(user=user)
            .order_by("-created_at")
            .first()
        )

        # OTP missing
        if not otp:

            request.session.pop("otp_user_id", None)
            request.session.pop("otp_attempts", None)

            return render(request, self.template_name, {
                "error": "OTP not found. Please request a new one."
            })

        # OTP expired
        if otp.is_expired():

            EmailOTP.objects.filter(pk=otp.pk).delete()

            request.session.pop("otp_user_id", None)
            request.session.pop("otp_attempts", None)

            return render(request, self.template_name, {
                "error": "OTP expired. Please request a new one."
            })

        # Verify OTP
        if check_password(code, otp.code):

            # Delete OTP immediately (single-use)
            EmailOTP.objects.filter(pk=otp.pk).delete()

            # Login user
            login(request, user)

            # Clear session temp data
            request.session.pop("otp_user_id", None)
            request.session.pop("otp_attempts", None)

            return redirect("list_problems")

        # Failed attempt
        attempts += 1

        request.session["otp_attempts"] = attempts

        return render(request, self.template_name, {
            "error": f"Invalid code. Attempts left: {MAX_ATTEMPTS - attempts}"
        })

# =========================
# RESEND OTP
# =========================
class ResendOTPView(View):

    def post(self, request):
        user_id = request.session.get("otp_user_id")

        if not user_id:
            return JsonResponse({"error": "Session expired"}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        generate_and_send_otp(user, request)

        return JsonResponse({"status": "resent"})

# ---------------------------
# PROFILE VIEW
# ---------------------------

@method_decorator(login_required, name="dispatch")
class ProfileView(View):
    template_name = "profile.html"

    def get(self, request, user_id):
        user_obj = get_object_or_404(User, id=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=user_obj)

        # Check if logged-in user follows this profile
        is_following = False
        if request.user.is_authenticated and request.user != user_obj:
            is_following = Follow.objects.filter(
                follower=request.user,
                following=user_obj
            ).exists()

        # TOTAL TIPS RECEIVED (answers + problems)
        total_tips = Tip.objects.filter(
            receiver=user_obj
        ).aggregate(total=Sum("amount"))["total"] or 0
        
        total_bounties = Problem.objects.filter(
            answers__is_accepted=True,
            answers__author=user_obj
        ).aggregate(total=Sum("bounty_amount"))["total"] or 0

        # Calculate tier dynamically
        tier = ReputationService.calculate_tier(getattr(user_obj, "reputation_score", 0))
        
        status = ExpertVerificationService.eligibility_status(request.user)
        
        profile_data = {
            "username": user_obj.username,
            "first_name": user_obj.first_name,
            "last_name": user_obj.last_name,
            "email": user_obj.email if request.user == user_obj else None,
            "reputation_score": getattr(user_obj, "reputation_score", 0),
            "tier": tier,   # <-- include tier here
            "is_verified_expert": getattr(user_obj, "is_verified_expert", False),

            "is_verification_recurring": (
                profile.is_verification_recurring
            ),

            "verified_until": profile.verified_until,
            "profession": profile.profession,
            "country": profile.country,
            "website": profile.website,
            "bio": getattr(user_obj, "bio", ""),
            "followers_count": profile.followers_count,
            "following_count": profile.following_count,
            "avatar_url": user_obj.avatar.url if getattr(user_obj, "avatar", None) else None,
            "is_owner": request.user == user_obj,
            "is_following": is_following,

            # earnings
            "total_tips_received": total_tips,
            "total_bounties_earned": total_bounties,
        }

        return render(request, self.template_name, {
            "profile_user": user_obj,
            "profile": profile_data,
            "status": status,
        })
        

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View


@method_decorator(login_required, name="dispatch")
class ToggleVerificationRecurringView(LoginRequiredMixin, View):

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):

        user = request.user
        profile = user.profile

        # ONLY check expert status
        if not user.is_verified_expert:
            return JsonResponse({
                "success": False,
                "message": "You are not a verified expert."
            }, status=403)

        profile.is_verification_recurring = not profile.is_verification_recurring
        profile.save(update_fields=["is_verification_recurring"])

        return JsonResponse({
            "success": True,
            "recurring": profile.is_verification_recurring,
            "message": (
                "Recurring billing enabled."
                if profile.is_verification_recurring
                else "Recurring billing disabled."
            )
        })

# ---------------------------
# PROFILE ACTIVITY API
# ---------------------------

@method_decorator(login_required, name="dispatch")
class ProfileActivityAPI(View):
    """
    Returns paginated JSON for user's activity.
    Supports types: problems, answers, bounties, tips.
    Bounties and tips are only visible to the profile owner.
    """

    def get(self, request, user_id):

        user_obj = get_object_or_404(User, id=user_id)

        activity_type = request.GET.get("type", "problems")
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 5))

        items = []

        # ---------------------------
        # Problems
        # ---------------------------
        if activity_type == "problems":

            qs = Problem.objects.filter(
                author=user_obj
            ).order_by("-created_at")

            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(page)

            items = [{
                "title": p.title or "Untitled",
                "url": f"/problems/{p.id}/",
                "date": p.created_at.strftime("%b %d, %Y"),
                "votes": p.votes_score or 0,
                "answers": p.answers_count or 0,
                "views": p.views_count or 0,
            } for p in page_obj]

        # ---------------------------
        # Answers
        # ---------------------------
        elif activity_type == "answers":

            qs = Answer.objects.select_related(
                "problem"
            ).filter(
                author=user_obj
            ).order_by("-created_at")

            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(page)

            items = [{
                "problemTitle": a.problem.title if a.problem else "Untitled",
                "problemUrl": f"/problems/{a.problem.id}/" if a.problem else "#",
                "content": a.content or "",
                "date": a.created_at.strftime("%b %d, %Y"),
            } for a in page_obj]

        # ---------------------------
        # Bounties (owner only)
        # ---------------------------
        elif activity_type == "bounties":

            if request.user != user_obj:
                return JsonResponse({"items": []})

            qs = Problem.objects.select_related(
                "author"
            ).filter(
                answers__is_accepted=True,
                answers__author=user_obj
            ).order_by("-created_at").distinct()

            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(page)

            items = [{
                "problemTitle": p.title if p.title else "Untitled",
                "problemUrl": f"/problems/{p.id}/",
                "amount": float(getattr(p, "bounty_amount", 0)),
                "date": p.created_at.strftime("%b %d, %Y"),
            } for p in page_obj]

        # ---------------------------
        # Tips (owner only)
        # ---------------------------
        elif activity_type == "tips":

            if request.user != user_obj:
                return JsonResponse({"items": []})

            qs = Tip.objects.select_related(
                "problem",
                "answer"
            ).filter(
                receiver=user_obj
            ).order_by("-created_at")

            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(page)

            items = [{
                "problemTitle": (
                    t.problem.title if t.problem else
                    t.answer.problem.title if t.answer else
                    "Untitled"
                ),
                "problemUrl": (
                    f"/problems/{t.problem.id}/" if t.problem else
                    f"/problems/{t.answer.problem.id}/" if t.answer else
                    "#"
                ),
                "answerContent": t.answer.content if t.answer else "",
                "amount": float(t.amount),
                "date": t.created_at.strftime("%b %d, %Y"),
            } for t in page_obj]

        return JsonResponse({
            "items": items
        })
        
# ---------------------------

@method_decorator(login_required, name="dispatch")
class UpdateProfileView(View):
    template_name = "update_profile.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect(reverse("login"))

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        initial_data = {"bio": getattr(request.user, "bio", "")}
        form = UpdateProfileForm(instance=profile, initial=initial_data)

        return render(request, self.template_name, {
            "form": form,
            "avatar_url": request.user.avatar.url if request.user.avatar else None
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect(reverse("login"))

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form = UpdateProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            updated_profile = form.save(commit=False)

            # Update User fields
            request.user.bio = form.cleaned_data.get("bio", getattr(request.user, "bio", ""))

            # Handle avatar upload on User model
            avatar_file = form.cleaned_data.get("avatar")
            if avatar_file:
                img = Image.open(avatar_file)
                img = img.convert("RGBA")
                img.thumbnail((300, 300))

                buffer = BytesIO()
                img.save(buffer, format="PNG")
                buffer.seek(0)

                filename = f"{request.user.username}_avatar.png"
                request.user.avatar.save(filename, ContentFile(buffer.read()), save=False)

            # Save both User and UserProfile
            request.user.save()
            updated_profile.save()

            # Redirect to profile with user_id
            return redirect("profile", user_id=request.user.id)

        return render(request, self.template_name, {
            "form": form,
            "avatar_url": request.user.avatar.url if request.user.avatar else None
        })
   
@method_decorator(login_required, name="dispatch")
class DeleteProfileView(LoginRequiredMixin, View):
    def post(self, request):
        confirmation = request.POST.get("confirmation", "")

        if confirmation != "DELETE":
            messages.error(
                request,
                "Type DELETE to confirm account deletion."
            )
            return redirect("update_profile")

        user = request.user

        logout(request)

        user.delete()

        messages.success(request, "Account deleted successfully.")
        return redirect("login")
    
    
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views import View
import json

@method_decorator(login_required, name="dispatch")
class VerifyDeletePasswordView(View):

    def post(self, request):

        data = json.loads(request.body)

        password = data.get("password")

        user = authenticate(
            username=request.user.username,
            password=password
        )

        return JsonResponse({
            "success": bool(user)
        })
        
# ---------------------------
# LOGOUT VIEW
# ---------------------------

@method_decorator(login_required, name="dispatch") 
class LogoutView(View):
    def get(self, request):
        logout(request)
        if request.content_type == "application/json":
            return JsonResponse({"status": "logged_out"})
        return redirect(reverse("login"))
    
    
    
from django.urls import reverse

@method_decorator(login_required, name="dispatch")
class UpdateAvailabilityView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = UserProfile
    template_name = "profile/update_availability.html"

    fields = [
        "availability_status",
        "availability_reason",
        "availability_mode",
    ]

    def test_func(self):
        return self.get_object().user == self.request.user

    def form_valid(self, form):
        status = form.cleaned_data["availability_status"]
        mode = form.cleaned_data["availability_mode"]

        # 🔴 business rule
        if status == "offline":
            form.instance.availability_reason = ""

        # 🧠 enforce logic
        if mode == "onsite" and status == "later":
            form.instance.availability_status = "online"

        return super().form_valid(form)

    # ✅ THIS FIXES YOUR ERROR
    def get_success_url(self):
        return self.request.META.get(
            "HTTP_REFERER",
            reverse("profile", kwargs={"user_id": self.object.user.id})
        )
        
        

from django.db.models import Case, When, IntegerField, Value, Exists, OuterRef
from django.utils import timezone


@method_decorator(login_required, name="dispatch")
class ExpertSearchView(ListView):
    model = UserProfile
    template_name = "search/experts.html"
    context_object_name = "experts"

    def get_queryset(self):
        from django.db.models import Exists, OuterRef, Case, When, Value, IntegerField
        from django.utils import timezone

        qs = UserProfile.objects.select_related("user")

        # 🚫 EXCLUDE CURRENT USER + SUPERUSERS + STAFF
        qs = qs.exclude(
            user=self.request.user
        ).exclude(
            user__is_superuser=True
        ).exclude(
            user__is_staff=True
        )

        # ✅ SIMPLE & CORRECT: only check non-archived future slots
        active_slots_qs = AvailabilitySlot.objects.filter(
            expert_id=OuterRef("user_id"),
            is_archived=False,
            start_time__gt=timezone.now()
        )

        qs = qs.annotate(
            has_active_slots=Exists(active_slots_qs)
        )

        # FILTERS
        status = self.request.GET.get("status")
        reason = self.request.GET.get("reason")
        mode = self.request.GET.get("mode")
        location = self.request.GET.get("location")

        if status:
            qs = qs.filter(availability_status=status)

        if reason:
            qs = qs.filter(availability_reason=reason)

        if mode:
            qs = qs.filter(availability_mode=mode)

        if mode == "onsite" and location:
            qs = qs.filter(country__icontains=location)

        # 🔥 PRIORITY SORTING
        qs = qs.annotate(
            status_priority=Case(
                When(availability_status="online", then=Value(3)),
                When(availability_status="later", then=Value(2)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )

        return qs.order_by(
            "-has_active_slots",   # ✅ experts with slots first
            "-status_priority",
            "-updated_at",
            "-user__reputation_score"
        )

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            return render(
                self.request,
                "partials/expert_list.html",
                context
            )
        return super().render_to_response(context, **response_kwargs)


@method_decorator(login_required, name="dispatch")
class ReportUserView(View):

    # =========================================================
    # SHOW REPORT PAGE
    # =========================================================
    def get(self, request):

        return render(request, "report_user.html")

    # =========================================================
    # HANDLE REPORT SUBMISSION
    # =========================================================
    def post(self, request):

        reporter = request.user

        reported_username = request.POST.get(
            "reported_username",
            ""
        ).strip()

        reason = request.POST.get(
            "reason",
            ""
        ).strip()

        evidence = request.FILES.get("evidence_image")

        # =========================================================
        # VALIDATION
        # =========================================================
        if not reported_username:

            return render(request, "report_user.html", {
                "error": "Reported username is required."
            })

        if not reason:

            return render(request, "report_user.html", {
                "error": "Reason is required."
            })

        # =========================================================
        # FIND USER
        # =========================================================
        try:
            reported_user = User.objects.get(
                username=reported_username
            )

        except User.DoesNotExist:

            return render(request, "report_user.html", {
                "error": "The user you entered does not exist."
            })

        # =========================================================
        # PREVENT SELF REPORT
        # =========================================================
        if reported_user == reporter:

            return render(request, "report_user.html", {
                "error": "You cannot report yourself."
            })

        # =========================================================
        # CREATE REPORT
        # =========================================================
        report = UserReport.objects.create(
            reporter=reporter,
            reported_user=reported_user,
            reason=reason,
            evidence_image=evidence
        )

        # =========================================================
        # EVIDENCE LINK
        # =========================================================
        evidence_html = ""

        if report.evidence_image:

            evidence_html = f"""
            <div style="
                margin-top:20px;
                padding:18px;
                background:#f8f9fa;
                border-radius:10px;
                border:1px solid #e5e7eb;
            ">

                <h3 style="
                    margin-top:0;
                    color:#dc3545;
                    font-size:18px;
                ">
                    Attached Evidence
                </h3>

                <p style="margin-bottom:15px;color:#555;">
                    The reporter attached supporting evidence.
                </p>

                <a href="{report.evidence_image.url}"
                   target="_blank"
                   style="
                        display:inline-block;
                        padding:12px 18px;
                        background:#dc3545;
                        color:white;
                        text-decoration:none;
                        border-radius:8px;
                        font-weight:600;
                   ">
                    Open Evidence
                </a>

            </div>
            """

        # =========================================================
        # ADMIN EMAIL HTML
        # =========================================================
        admin_html = f"""
        <div style="
            background:#f4f6f9;
            padding:40px 20px;
            font-family:Arial,sans-serif;
        ">

            <div style="
                max-width:720px;
                margin:auto;
                background:white;
                border-radius:16px;
                overflow:hidden;
                box-shadow:0 8px 25px rgba(0,0,0,0.08);
            ">

                <!-- HEADER -->
                <div style="
                    background:linear-gradient(135deg,#dc3545,#b91c1c);
                    padding:30px;
                    color:white;
                    text-align:center;
                ">

                    <h1 style="
                        margin:0;
                        font-size:28px;
                    ">
                        🚨 New User Report
                    </h1>

                    <p style="
                        margin-top:10px;
                        opacity:0.9;
                    ">
                        FancyLearn Trust & Safety Notification
                    </p>

                </div>

                <!-- BODY -->
                <div style="padding:35px;">

                    <div style="
                        background:#fff5f5;
                        border-left:4px solid #dc3545;
                        padding:18px;
                        border-radius:10px;
                        margin-bottom:25px;
                    ">
                        A new moderation report has been submitted and requires review.
                    </div>

                    <!-- REPORTER -->
                    <h2 style="color:#dc3545;">
                        Reporter Information
                    </h2>

                    <table style="
                        width:100%;
                        border-collapse:collapse;
                        margin-bottom:30px;
                    ">
                        <tr>
                            <td style="padding:10px 0;"><strong>Username</strong></td>
                            <td>{reporter.username}</td>
                        </tr>

                        <tr>
                            <td style="padding:10px 0;"><strong>Email</strong></td>
                            <td>{reporter.email}</td>
                        </tr>
                    </table>

                    <!-- REPORTED USER -->
                    <h2 style="color:#dc3545;">
                        Reported User
                    </h2>

                    <table style="
                        width:100%;
                        border-collapse:collapse;
                        margin-bottom:30px;
                    ">
                        <tr>
                            <td style="padding:10px 0;"><strong>Username</strong></td>
                            <td>{reported_user.username}</td>
                        </tr>

                        <tr>
                            <td style="padding:10px 0;"><strong>Email</strong></td>
                            <td>{reported_user.email}</td>
                        </tr>
                    </table>

                    <!-- REASON -->
                    <h2 style="color:#dc3545;">
                        Report Reason
                    </h2>

                    <div style="
                        background:#f8fafc;
                        border:1px solid #e5e7eb;
                        padding:20px;
                        border-radius:12px;
                        line-height:1.8;
                        color:#374151;
                    ">
                        {reason}
                    </div>

                    {evidence_html}

                </div>

                <!-- FOOTER -->
                <div style="
                    background:#111827;
                    padding:30px;
                    color:#d1d5db;
                    text-align:center;
                    font-size:13px;
                ">

                    <p style="margin:0 0 10px 0;">
                        This email was automatically generated by FancyLearn.
                    </p>

                    <p style="margin:0;">
                        © 2026 FancyLearn • Trust & Safety Team
                    </p>

                </div>

            </div>

        </div>
        """

        # =========================================================
        # REPORTER RECEIPT EMAIL
        # =========================================================
        reporter_html = f"""
        <div style="
            background:#f4f6f9;
            padding:40px 20px;
            font-family:Arial,sans-serif;
        ">

            <div style="
                max-width:680px;
                margin:auto;
                background:white;
                border-radius:16px;
                overflow:hidden;
                box-shadow:0 8px 25px rgba(0,0,0,0.08);
            ">

                <!-- HEADER -->
                <div style="
                    background:linear-gradient(135deg,#2563eb,#1d4ed8);
                    color:white;
                    text-align:center;
                    padding:30px;
                ">

                    <h1 style="margin:0;">
                        Report Received
                    </h1>

                    <p style="margin-top:10px;opacity:0.9;">
                        Thank you for helping keep FancyLearn safe.
                    </p>

                </div>

                <!-- BODY -->
                <div style="padding:35px;">

                    <p style="
                        font-size:16px;
                        color:#374151;
                        line-height:1.8;
                    ">
                        Hello <strong>{reporter.username}</strong>,
                    </p>

                    <p style="
                        color:#4b5563;
                        line-height:1.8;
                    ">
                        We have successfully received your report regarding
                        <strong>{reported_user.username}</strong>.
                    </p>

                    <div style="
                        background:#eff6ff;
                        border-left:4px solid #2563eb;
                        padding:18px;
                        border-radius:10px;
                        margin:25px 0;
                        color:#1e3a8a;
                    ">
                        Our Trust & Safety team is currently reviewing the report.
                        If necessary, appropriate moderation actions will be taken.
                    </div>

                    <p style="
                        color:#6b7280;
                        line-height:1.8;
                    ">
                        Please avoid submitting duplicate or false reports.
                        Abuse of the reporting system may result in account restrictions.
                    </p>

                </div>

                <!-- FOOTER -->
                <div style="
                    background:#111827;
                    padding:30px;
                    text-align:center;
                    color:#d1d5db;
                    font-size:13px;
                ">

                    <p style="margin:0 0 10px 0;">
                        FancyLearn Trust & Safety Team
                    </p>

                    <p style="margin:0;">
                        © 2026 FancyLearn. All rights reserved.
                    </p>

                </div>

            </div>

        </div>
        """

        # =========================================================
        # SEND ADMIN EMAIL
        # =========================================================
        admin_email = EmailMultiAlternatives(
            subject=f"🚨 New User Report - {reported_user.username}",
            body=strip_tags(admin_html),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.ADMIN_EMAIL]
        )

        admin_email.attach_alternative(
            admin_html,
            "text/html"
        )

        # attach evidence
        if evidence:

            evidence.seek(0)

            admin_email.attach(
                evidence.name,
                evidence.read(),
                evidence.content_type
            )

        admin_email.send(fail_silently=False)

        # =========================================================
        # SEND REPORT RECEIPT TO REPORTER
        # =========================================================
        receipt_email = EmailMultiAlternatives(
            subject="Your report is under review • FancyLearn",
            body=strip_tags(reporter_html),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[reporter.email]
        )

        receipt_email.attach_alternative(
            reporter_html,
            "text/html"
        )

        receipt_email.send(fail_silently=False)

        # =========================================================
        # SUCCESS RESPONSE
        # =========================================================
        return render(request, "report_user.html", {
            "success": (
                "Your report has been submitted successfully. "
                "A confirmation email has been sent to you."
            )
        })
        
        
        
@method_decorator(login_required, name="dispatch")
class VerifyPasswordAjax(View):



    def post(self, request):



        try:

            data = json.loads(request.body)

        except:

            return JsonResponse({"valid": False})



        password = data.get("password")



        user = authenticate(

            username=request.user.username,

            password=password

        )



        if not user:

            return JsonResponse({"valid": False})



        request.session["email_change_password_ok"] = True



        return JsonResponse({"valid": True})





@method_decorator(login_required, name="dispatch")

class SendEmailChangeOTPView(View):



    def post(self, request):



        if not request.session.get("email_change_password_ok"):

            return JsonResponse({"valid": False})



        try:

            data = json.loads(request.body)

        except:

            return JsonResponse({"valid": False})



        new_email = data.get("email", "").strip()



        if not new_email:

            return JsonResponse({"valid": False})



        # store pending email

        request.session["pending_new_email"] = new_email



        # 🔥 USE SAME OTP SYSTEM AS LOGIN

        generate_and_send_otp(request.user, request)



        request.session["email_change_otp_sent"] = True



        return JsonResponse({

            "valid": True,

            "otp_sent": True

        })





@method_decorator(login_required, name="dispatch")

class VerifyEmailChangeOTPView(View):



    def post(self, request):



        if not request.session.get("email_change_otp_sent"):

            return JsonResponse({"valid": False})



        try:

            data = json.loads(request.body.decode("utf-8") or "{}")

        except:

            return JsonResponse({"valid": False})



        otp_code = data.get("otp", "").strip()



        user = request.user



        otp = (

            EmailOTP.objects

            .filter(user=user)

            .order_by("-created_at")

            .first()

        )



        if not otp:

            return JsonResponse({"valid": False})



        if otp.is_expired():

            otp.delete()

            return JsonResponse({"valid": False})



        if check_password(otp_code, otp.code):



            otp.delete()

            request.session["email_change_verified"] = True



            return JsonResponse({"valid": True})



        return JsonResponse({"valid": False})


@method_decorator(login_required, name="dispatch")
class UpdateEmailView(View):



    def post(self, request):



        if not request.session.get("email_change_verified"):

            return redirect("profile")



        new_email = request.session.get("pending_new_email")



        if not new_email:

            return redirect("profile")



        request.user.email = new_email

        request.user.save()



        # cleanup session

        request.session.pop("email_change_password_ok", None)

        request.session.pop("email_change_otp_sent", None)

        request.session.pop("email_change_verified", None)

        request.session.pop("pending_new_email", None)



        messages.success(request, "Email updated successfully.")



        return redirect("profile", user_id=request.user.id)