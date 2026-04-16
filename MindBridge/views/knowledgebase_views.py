from django.views import View
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from MindBridge.models import KnowledgeBaseEntry
from collections import defaultdict


@method_decorator(login_required, name="dispatch")
class KnowledgeBaseView(View):
    template_name = "knowledgebase.html"

    def get(self, request):
        search = request.GET.get("search", "").strip()
        entry_id = request.GET.get("entry")

        # ---------------------------------------
        # BASE QUERY
        # ---------------------------------------
        kb_qs = KnowledgeBaseEntry.objects.select_related(
            "problem", "answer"
        ).order_by("-created_at")

        # ---------------------------------------
        # SEARCH
        # ---------------------------------------
        if search:
            kb_qs = kb_qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        # ---------------------------------------
        # GROUP + SORT CATEGORIES
        # ---------------------------------------
        categories = defaultdict(list)

        # Group entries
        for entry in kb_qs:
            categories[entry.category or "General"].append(entry)

        # Sort entries inside each category (A → Z)
        for category in categories:
            categories[category] = sorted(
                categories[category],
                key=lambda x: x.title.lower()
            )

        # Sort categories alphabetically
        categories = dict(
            sorted(categories.items(), key=lambda x: x[0].lower())
        )

        # ---------------------------------------
        # SELECTED ENTRY (FIXED LOGIC)
        # ---------------------------------------
        selected_entry = None

        if entry_id:
            selected_entry = kb_qs.filter(id=entry_id).first()
        else:
            # Select first entry from sorted categories
            for entries in categories.values():
                if entries:
                    selected_entry = entries[0]
                    break

        # ---------------------------------------
        # CONTEXT
        # ---------------------------------------
        return render(request, self.template_name, {
            "categories": categories,
            "entry": selected_entry,
            "search": search,
            "selected_entry_id": str(selected_entry.id) if selected_entry else None
        })