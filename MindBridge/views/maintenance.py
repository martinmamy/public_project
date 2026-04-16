from django.views.generic import TemplateView
from django.urls import resolve, Resolver404

from public_project import settings

class MaintenancePageView(TemplateView):
    template_name = "maintenance_page.html"
    
from django.shortcuts import render

def custom_404_view(request, exception):
    if settings.DEBUG:
        return render(request, "missing_page_dev.html", status=404)
    return render(request, "missing_page.html", status=404)

class MissingDataPageView(TemplateView):
    template_name = "missing_page_dev.html"