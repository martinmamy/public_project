from django.views import View
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import F
from datetime import datetime
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from MindBridge.models import Problem
from MindBridge.services.feed_service import (
    get_global_feed,
    get_trending_feed,
    get_personalized_feed,
    get_following_feed,
    get_followers_feed,
    get_tips_analytics, get_bounties_analytics, get_financial_summary
)


@method_decorator(login_required, name="dispatch")
class FeedsPageView(View):
    def get(self, request):
        user = request.user

        # -----------------------------
        # Query params
        # -----------------------------
        problem_id = request.GET.get("problem_id")
        year = request.GET.get("year")
        month = request.GET.get("month")

        try:
            year = int(year)
        except (TypeError, ValueError):
            year = datetime.now().year

        try:
            month = int(month)
        except (TypeError, ValueError):
            month = None

        # -----------------------------
        # Fetch feeds
        # -----------------------------
        global_problems = []
        trending_problems = []
        personalized_problems = []
        following_users = []
        followers_users = []

        # 🆕 Financial data
        tips_analytics = {"earnings": [], "spending": []}
        bounties_analytics = {"earnings": [], "spending": []}
        financial_summary = {}

        if user.is_authenticated:
            global_problems = get_global_feed(user, limit=50, year=year, month=month)
            trending_problems = get_trending_feed(user, limit=10, year=year, month=month)
            personalized_problems = get_personalized_feed(user, limit=50, year=year, month=month)
            following_users = get_following_feed(user, limit=None, year=year, month=month)
            followers_users = get_followers_feed(user, limit=None, year=year, month=month)

            # 🆕 Financial feeds
            tips_analytics = get_tips_analytics(user, year=year, month=month)
            bounties_analytics = get_bounties_analytics(user, year=year, month=month)
            financial_summary = get_financial_summary(user)

        # -----------------------------
        # Selected problem
        # -----------------------------
        selected_problem = None
        if problem_id:
            try:
                selected_problem = get_object_or_404(Problem, id=problem_id)
            except ValueError:
                selected_problem = None
        elif global_problems:
            selected_problem = global_problems[0]

        # -----------------------------
        # Month / Year lists
        # -----------------------------
        month_list = [
            "January","February","March","April","May","June",
            "July","August","September","October","November","December"
        ]
        year_list = list(range(2020, 2031))

        # -----------------------------
        # Aggregate following/followers
        # -----------------------------
        def aggregate_users_by_month(users):
            data = {}
            for u in users:
                join_date = getattr(u, "date_joined", None)
                if not join_date or join_date.year != year:
                    continue
                month_number = join_date.month
                data[month_number] = data.get(month_number, 0) + 1
            return data

        following_counts = aggregate_users_by_month(following_users)
        followers_counts = aggregate_users_by_month(followers_users)

        follow_chart_data = []
        for m in range(1, 13):
            follow_chart_data.append({
                "month": m,
                "year": year,
                "following_count": following_counts.get(m, 0),
                "followers_count": followers_counts.get(m, 0),
                "label": month_list[m-1]
            })

        # -----------------------------
        # 🆕 Normalize financial chart data (important for frontend)
        # -----------------------------
        def normalize_financial_data(data):
            mapped = {item["date"].month: float(item["total"]) for item in data if item["date"]}
            return [mapped.get(m, 0) for m in range(1, 13)]

        tips_chart = {
            "earnings": normalize_financial_data(tips_analytics["earnings"]),
            "spending": normalize_financial_data(tips_analytics["spending"]),
        }

        bounties_chart = {
            "earnings": normalize_financial_data(bounties_analytics["earnings"]),
            "spending": normalize_financial_data(bounties_analytics["spending"]),
        }

        # -----------------------------
        # Context
        # -----------------------------
        context = {
            # Existing feeds
            "problems": global_problems,
            "trending_problems": trending_problems,
            "personalized_problems": personalized_problems,
            "following_problems": follow_chart_data,
            "followers_problems": followers_users,
            "selected_problem": selected_problem,

            # Filters
            "month": month,
            "year": year,
            "month_list": month_list,
            "year_list": year_list,
            "current_year": datetime.now().year,

            # 🆕 Financial UI
            "tips_chart": tips_chart,
            "bounties_chart": bounties_chart,
            "financial_summary": financial_summary,
        }

        return render(request, "feeds.html", context)


# =====================================================
# AJAX Increment Views
# =====================================================

@method_decorator(login_required, name="dispatch")
class ProblemIncrementView(View):
    def post(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)
        Problem.objects.filter(id=problem.id).update(views_count=F("views_count") + 1)
        problem.refresh_from_db()
        return JsonResponse({"views": problem.views_count})


# =====================================================
# JSON API ENDPOINTS
# =====================================================

@method_decorator(login_required, name="dispatch")
class GlobalFeedView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "login required"}, status=401)

        year = request.GET.get("year")
        month = request.GET.get("month")
        try: year = int(year)
        except: year = None
        try: month = int(month)
        except: month = None

        problems = get_global_feed(request.user, limit=20, year=year, month=month)

        data = [
            {
                "id": str(p.id),
                "title": p.title,
                "author": p.author.username,
                "votes": getattr(p, "votes_score", 0),
                "answers": getattr(p, "answers_count", 0),
                "views": getattr(p, "views_count", 0),
                "created_at": p.created_at.isoformat(),
            } for p in problems
        ]
        return JsonResponse(data, safe=False)



@method_decorator(login_required, name="dispatch")
class TrendingFeedView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "login required"}, status=401)

        year = request.GET.get("year")
        month = request.GET.get("month")
        try: year = int(year)
        except: year = None
        try: month = int(month)
        except: month = None

        problems = get_trending_feed(request.user, limit=10, year=year, month=month)

        data = [
            {
                "id": str(p.id),
                "title": p.title,
                "author": p.author.username,
                "score": getattr(p, "trending_score", 0),
                "votes": getattr(p, "votes_score", 0),
                "answers": getattr(p, "answers_count", 0),
                "views": getattr(p, "views_count", 0),
                "created_at": p.created_at.isoformat(),
            } for p in problems
        ]
        return JsonResponse(data, safe=False)



@method_decorator(login_required, name="dispatch")
class PersonalizedFeedView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "login required"}, status=401)

        year = request.GET.get("year")
        month = request.GET.get("month")
        try: year = int(year)
        except: year = None
        try: month = int(month)
        except: month = None

        problems = get_personalized_feed(request.user, limit=20, year=year, month=month)

        data = [
            {
                "id": str(p.id),
                "title": p.title,
                "author": p.author.username,
                "votes": getattr(p, "votes_score", 0),
                "answers": getattr(p, "answers_count", 0),
                "views": getattr(p, "views_count", 0),
                "created_at": p.created_at.isoformat(),
            } for p in problems
        ]
        return JsonResponse(data, safe=False)