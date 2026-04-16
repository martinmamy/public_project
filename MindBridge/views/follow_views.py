from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from MindBridge.models import User, Follow
from MindBridge.services.notification_service import NotificationService
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required


def serialize_user(u):
    return {
        "id": u.id,
        "username": u.username,
        "avatar_url": u.avatar.url if u.avatar else None,
    }    

@method_decorator(login_required, name="dispatch")
class FollowUserView(View):
    def post(self, request, user_id):
        user_to_follow = get_object_or_404(User, id=user_id)

        follow, created = Follow.objects.get_or_create(
            follower=request.user,
            following=user_to_follow
        )

        if created:
            # Generate the correct profile URL
            profile_url = reverse("profile", args=[request.user.id])  # <-- use reverse

            # Notify the followed user
            NotificationService.create_notification(
                user=user_to_follow,        # recipient
                actor=request.user,         # the follower
                message=f"{request.user.username} started following you.",
                url=profile_url
            )

        return JsonResponse({"status": "followed"})


@method_decorator(login_required, name="dispatch")
class UnfollowUserView(View):

    def post(self, request, user_id):

        user = get_object_or_404(User, id=user_id)

        Follow.objects.filter(
            follower=request.user,
            following=user
        ).delete()

        return JsonResponse({"status": "unfollowed"})

        
        
# ------------------------
# Followers API
# ------------------------
# ------------------------
# Followers API
# ------------------------

@method_decorator(login_required, name="dispatch")
class ProfileFollowersAPI(View):
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        followers_qs = user.followers.all()  # Assuming related_name='followers' on Follow model
        followers_list = [
            {
                "id": f.follower.id,
                "username": f.follower.username,
                "avatar_url": f.follower.avatar.url if f.follower.avatar else None,  # <-- key fixed
            }
            for f in followers_qs
        ]
        return JsonResponse({"items": followers_list})

# ------------------------
# Following API
# ------------------------

@method_decorator(login_required, name="dispatch")
class ProfileFollowingAPI(View):
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        following_qs = user.following.all()  # Assuming related_name='following' on Follow model
        following_list = [
            {
                "id": f.following.id,
                "username": f.following.username,
                "avatar_url": f.following.avatar.url if f.following.avatar else None,  # <-- key fixed
            }
            for f in following_qs
        ]
        return JsonResponse({"items": following_list})
                
            
            
        
        
