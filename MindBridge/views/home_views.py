from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from MindBridge.views.comment_views import LoginRequiredMixin

class HomePageView(TemplateView):
    template_name = "home.html"


method_decorator(login_required, name="dispatch")
class settingsPageView(LoginRequiredMixin, TemplateView):
    template_name = "settings.html"