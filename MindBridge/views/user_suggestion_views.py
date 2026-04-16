# views/user_suggestion.py
from django.views import View
from django.http import JsonResponse
from MindBridge.models import User
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required


@method_decorator(login_required, name="dispatch")
class UserSuggestionView(View):
    """
    Return a list of usernames matching a partial query for @mentions.
    Excludes the current user.
    """

    def get(self, request):
        query = request.GET.get("q", "").strip()
        if not query:
            return JsonResponse({"users": []})

        users = (
            User.objects
            .filter(username__istartswith=query)
            .exclude(id=request.user.id if request.user.is_authenticated else None)
            [:10]  # limit results
        )

        user_list = [
            {
                "id": u.id,
                "username": u.username,
                "avatar_url": u.avatar.url if u.avatar else None,  # include avatar
            }
            for u in users
        ]

        return JsonResponse({"users": user_list})