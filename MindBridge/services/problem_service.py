from django.db import transaction
from django.db.models import F
from django.utils.text import slugify

from MindBridge.models import Problem, Tag, ProblemMedia


class ProblemService:

    @staticmethod
    @transaction.atomic
    def create_problem(author, title, description, category, tags=None, media_files=None):
        problem = Problem.objects.create(
            author=author,
            title=title,
            description=description,
            category=category
        )

        if tags:
            tag_objs = Tag.objects.filter(id__in=tags)
            problem.tags.add(*tag_objs)

        if media_files:
            for file in media_files:
                ProblemMedia.objects.create(problem=problem, file=file)

        return problem


    @staticmethod
    @transaction.atomic
    def update_problem(problem, title=None, description=None, category=None, tags=None):

        if title:
            problem.title = title

        if description:
            problem.description = description

        if category:
            problem.category = category

        problem.save()

        if tags is not None:
            tag_objs = Tag.objects.filter(id__in=tags)
            problem.tags.set(tag_objs)

        return problem


    @staticmethod
    @transaction.atomic
    def mark_problem_solved(problem, answer):
        problem.is_solved = True
        problem.save(update_fields=["is_solved"])

        answer.is_accepted = True
        answer.save(update_fields=["is_accepted"])


    @staticmethod
    def increment_views(problem):
        Problem.objects.filter(id=problem.id).update(
            views_count=F("views_count") + 1
        )