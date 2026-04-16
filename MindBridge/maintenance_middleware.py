from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
import os


class MaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_ip = request.META.get('REMOTE_ADDR')
        
        # Check if maintenance mode is enabled and user's IP is not in the whitelist
        if settings.MAINTENANCE_MODE and user_ip not in settings.MAINTENANCE_WHITELIST:
            # Redirect to maintenance page if not already on it
            if not request.path_info.startswith(reverse('app')):
                return HttpResponseRedirect(reverse('app'))
        
        # Allow the request to proceed if not in maintenance mode or IP is whitelisted
        response = self.get_response(request)
        return response
