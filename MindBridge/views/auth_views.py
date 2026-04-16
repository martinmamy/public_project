import json
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from MindBridge.middleware import settings
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from MindBridge.forms import RegisterForm, LoginForm, UpdateProfileForm
from MindBridge.models import UserProfile, Problem, EmailOTP, Answer, Bounty, Tip, Follow, User
from django.db.models import Sum
from MindBridge.services.expert_verification_service import ExpertVerificationService
from MindBridge.services.reputation_service import ReputationService
import random
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail


User = get_user_model()


# =========================
# OTP GENERATOR (REUSED)
# =========================
def generate_and_send_otp(user, request):
    code = str(random.randint(100000, 999999))

    EmailOTP.objects.filter(user=user).delete()

    EmailOTP.objects.create(
        user=user,
        code=make_password(code)
    )

    send_mail(
        "Your Verification Code",
        f"Your code is: {code}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

    request.session["otp_attempts"] = 0
    return code



# =========================
# OTP GENERATOR (EMAIL ONLY)
# =========================
def generate_and_send_otp_email_only(email, request):
    code = str(random.randint(100000, 999999))

    # store hashed OTP in session
    request.session["email_otp"] = make_password(code)
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

        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            from django.contrib.auth import get_user_model
            User = get_user_model()

            try:
                user_obj = User.objects.get(username__iexact=username)
                username = user_obj.username
            except User.DoesNotExist:
                user_obj = None

            user = authenticate(request, username=username, password=password)

            if user:

                if not user.is_active:
                    form.add_error(None, "Account not verified. Check your email.")
                    return render(request, self.template_name, {"form": form})

                request.session["otp_user_id"] = str(user.id)

                generate_and_send_otp(user, request)

                if request.content_type == "application/json":
                    return JsonResponse({"status": "otp_sent"})

                return redirect("verify_otp")

            form.add_error(None, "Invalid username or password")

        if request.content_type == "application/json":
            return JsonResponse({"errors": form.errors}, status=400)

        return render(request, self.template_name, {"form": form})

# =========================
# OTP LOGIN VERIFY VIEW
# =========================
MAX_ATTEMPTS = 3

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

        if attempts >= MAX_ATTEMPTS:
            request.session.flush()
            return render(request, self.template_name, {
                "error": "Too many failed attempts. Please login again."
            })

        code = request.POST.get("code")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return redirect("login")

        otp = EmailOTP.objects.filter(user=user).last()

        if otp and check_password(code, otp.code):
            login(request, user)

            otp.delete()
            request.session.pop("otp_user_id", None)
            request.session.pop("otp_attempts", None)

            return redirect("list_problems")

        request.session["otp_attempts"] = attempts + 1

        return render(request, self.template_name, {
            "error": f"Invalid code. Attempts left: {MAX_ATTEMPTS - (attempts + 1)}"
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
            "email": user_obj.email if request.user == user_obj else None,
            "reputation_score": getattr(user_obj, "reputation_score", 0),
            "tier": tier,   # <-- include tier here
            "is_verified_expert": getattr(user_obj, "is_verified_expert", False),
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