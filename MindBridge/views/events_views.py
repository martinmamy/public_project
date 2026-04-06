import uuid
import json
import os
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden, FileResponse, Http404
from django.urls import reverse
from django.db.models import Q, Count, Exists, OuterRef, Subquery, Prefetch
from django.utils import timezone
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from MindBridge.models import (
    Event,
    EventParticipant,
    EventRecording,
    EventInvitation,
    User
)

# -------------------------
# CREATE EVENT
# -------------------------

@method_decorator(login_required, name="dispatch")
class CreateEventView(LoginRequiredMixin, View):

    template_name = "create_event.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):

        title = request.POST.get("title")
        description = request.POST.get("description", "")
        is_public = request.POST.get("is_public") == "on"
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")

        if not title or not start_time:
            return render(
                request,
                self.template_name,
                {"error": "Title and start time are required"}
            )

        meeting_url = str(uuid.uuid4())

        event = Event.objects.create(
            host=request.user,
            title=title,
            description=description,
            is_public=is_public,
            start_time=start_time,
            end_time=end_time or None,
            meeting_url=meeting_url
        )

        EventParticipant.objects.get_or_create(
            event=event,
            user=request.user
        )

        return redirect(reverse("event_detail", args=[event.id]))


# -------------------------
# LIST EVENTS
# -------------------------

@method_decorator(login_required, name="dispatch")
class EventListView(LoginRequiredMixin, ListView):

    model = Event
    template_name = "event_list.html"
    context_object_name = "events"
    paginate_by = 20

    def get_queryset(self):

        user = self.request.user

        invited_subquery = EventInvitation.objects.filter(
            event=OuterRef('pk'),
            invited_user=user,
            accepted=False
        ).values('id')[:1]

        pending_invites_subquery = EventInvitation.objects.filter(
            event=OuterRef('pk'),
            accepted=False
        ).values('event').annotate(
            count=Count('id')
        ).values('count')

        queryset = Event.objects.filter(
            Q(is_public=True) |
            Q(host=user) |
            Q(invitations__invited_user=user)
        ).annotate(
            user_invited=Exists(invited_subquery),
            invite_id=Subquery(invited_subquery),
            pending_invites_count=Subquery(pending_invites_subquery)
        ).distinct().order_by("-created_at")

        return queryset


# -------------------------
# LIVE EVENTS LIST
# -------------------------

@method_decorator(login_required, name="dispatch")
class LiveEventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "live_events.html"
    context_object_name = "events"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Prefetch recordings to avoid N+1 queries
        recordings_prefetch = Prefetch(
            "recordings",
            queryset=Event.objects.filter(is_live=False)
        )

        queryset = Event.objects.filter(
            is_live=True
        ).filter(
            Q(host=user) | Q(invitations__invited_user=user)
        ).distinct().prefetch_related(recordings_prefetch).order_by("-created_at")

        return queryset

# -------------------------
# EVENT DETAIL
# -------------------------

@method_decorator(login_required, name="dispatch")
class EventDetailView(LoginRequiredMixin, DetailView):

    model = Event
    template_name = "event_detail.html"
    pk_url_kwarg = "event_id"
    context_object_name = "event"

    def dispatch(self, request, *args, **kwargs):

        event = self.get_object()

        if not event.is_public:

            invited = EventInvitation.objects.filter(
                event=event,
                invited_user=request.user
            ).exists()

            if request.user != event.host and not invited:
                return HttpResponseForbidden("You are not invited")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["is_host"] = self.request.user == self.object.host

        context["is_participant"] = EventParticipant.objects.filter(
            event=self.object,
            user=self.request.user
        ).exists()

        return context


# -------------------------
# START LIVE (HOST ONLY)
# -------------------------

@method_decorator(login_required, name="dispatch")
class StartLiveEventView(LoginRequiredMixin, View):

    def post(self, request, event_id):

        event = get_object_or_404(Event, id=event_id)

        if request.user != event.host:
            return JsonResponse({"error": "Not allowed"}, status=403)

        event.is_live = True
        event.save()

        return JsonResponse({"status": "live_started"})


# -------------------------
# STOP LIVE (HOST ONLY)
# -------------------------

@method_decorator(login_required, name="dispatch")
class StopLiveEventView(LoginRequiredMixin, View):

    def post(self, request, event_id):

        event = get_object_or_404(Event, id=event_id)

        if request.user != event.host:
            return JsonResponse({"error": "Not allowed"}, status=403)

        event.is_live = False
        event.save()

        return JsonResponse({"status": "live_stopped"})


# -------------------------
# JOIN EVENT
# -------------------------

@method_decorator(login_required, name="dispatch")
class JoinEventView(LoginRequiredMixin, View):

    def post(self, request, event_id):

        event = get_object_or_404(Event, id=event_id)

        # MUST BE LIVE
        if not event.is_live:
            return JsonResponse(
                {"error": "Event is not live yet"},
                status=403
            )

        # Check permissions
        if not event.is_public:

            invited = EventInvitation.objects.filter(
                event=event,
                invited_user=request.user,
                accepted=True
            ).exists()

            if request.user != event.host and not invited:
                return JsonResponse({"error": "Not invited"}, status=403)

        participant, created = EventParticipant.objects.get_or_create(
            event=event,
            user=request.user
        )

        return JsonResponse({
            "status": "joined" if created else "already_joined"
        })


# -------------------------
# INVITE USER
# -------------------------

@method_decorator(login_required, name="dispatch")
class InviteUserToEventView(LoginRequiredMixin, View):

    def post(self, request, event_id):

        if request.content_type != "application/json":
            return JsonResponse({"error": "Invalid request"}, status=400)

        data = json.loads(request.body)

        identifier = data.get("identifier", "").strip()

        event = get_object_or_404(Event, id=event_id)

        if request.user != event.host:
            return JsonResponse({"error": "Only host can invite"}, status=403)

        try:
            user = User.objects.get(
                Q(username=identifier) |
                Q(email=identifier)
            )
        except User.DoesNotExist:
            return JsonResponse({"status": "not_found"})

        invitation, created = EventInvitation.objects.get_or_create(
            event=event,
            invited_user=user,
            invited_by=request.user
        )

        return JsonResponse({
            "status": "invited" if created else "already_invited"
        })


# -------------------------
# ACCEPT INVITE
# -------------------------

@method_decorator(login_required, name="dispatch")
class AcceptEventInviteView(LoginRequiredMixin, View):

    def post(self, request, invite_id):

        invite = get_object_or_404(
            EventInvitation,
            id=invite_id,
            invited_user=request.user
        )

        invite.accepted = True
        invite.save()

        EventParticipant.objects.get_or_create(
            event=invite.event,
            user=request.user
        )

        return JsonResponse({"status": "accepted"})


# -------------------------
# STREAM VIDEO
# -------------------------

@method_decorator(login_required, name="dispatch")
class InternalLiveStreamView(LoginRequiredMixin, View):

    def get(self, request, event_id):

        event = get_object_or_404(Event, id=event_id)

        if not event.is_live:
            raise Http404("Stream not live")

        allowed = (
            request.user == event.host or
            EventParticipant.objects.filter(
                event=event,
                user=request.user
            ).exists()
        )

        if not allowed:
            return HttpResponseForbidden("Not allowed")

        video_filename = f"{event.id}.mp4"

        video_path = os.path.join(
            settings.MEDIA_ROOT,
            "live_streams",
            video_filename
        )

        if not os.path.exists(video_path):
            raise Http404("Stream not available")

        return FileResponse(
            open(video_path, "rb"),
            content_type="video/mp4"
        )


# -------------------------
# SAVE RECORDING
# -------------------------

@method_decorator(login_required, name="dispatch")
class SaveRecordingView(LoginRequiredMixin, View):

    def post(self, request, event_id):

        event = get_object_or_404(Event, id=event_id)

        if request.user != event.host:
            return JsonResponse(
                {"status": "error", "message": "Not authorized"},
                status=403
            )

        video_file = request.FILES.get("video")

        if not video_file:
            return JsonResponse(
                {"status": "error", "message": "No video file"},
                status=400
            )

        recording = EventRecording.objects.create(
            event=event,
            file=video_file
        )

        return JsonResponse({
            "status": "ok",
            "url": recording.file.url
        })


# -------------------------
# DELETE RECORDING
# -------------------------

@method_decorator(login_required, name="dispatch")
class DeleteRecordingView(LoginRequiredMixin, View):

    def post(self, request, pk):

        recording = get_object_or_404(EventRecording, pk=pk)

        if request.user != recording.event.host:
            return JsonResponse(
                {"status": "error", "message": "Not authorized"},
                status=403
            )

        recording.file.delete(save=False)
        recording.delete()

        return JsonResponse({"status": "ok"})


# -------------------------
# DELETE EVENT
# -------------------------

@method_decorator(login_required, name="dispatch")
class DeleteEventView(LoginRequiredMixin, View):

    def post(self, request, event_id):

        event = get_object_or_404(Event, id=event_id)

        if request.user != event.host:
            return JsonResponse(
                {"status": "error", "message": "Not authorized"},
                status=403
            )

        event.delete()

        return JsonResponse({
            "status": "ok",
            "message": "Event deleted"
        })
        
        
@method_decorator(login_required, name="dispatch")
class LeaveEventView(View):
    """
    Allow a user to leave a live event.
    For public events, users are added to participants when joining.
    """

    def post(self, request, event_id, *args, **kwargs):
        user = request.user
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return JsonResponse({"status":"error", "error":"Event not found"}, status=404)

        # Check if user is a participant or if event is public
        if user in event.participants.all():
            event.participants.remove(user)
            return JsonResponse({"status":"left"})
        elif event.is_public:
            # Allow leaving even if they were not pre-added
            return JsonResponse({"status":"left"})
        else:
            return JsonResponse({"status":"error", "error":"You are not a participant"}, status=400)

    def get(self, request, *args, **kwargs):
        return JsonResponse({"status":"error","error":"Invalid request"}, status=400)