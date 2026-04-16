from django.db.models.signals import pre_save
from django.dispatch import receiver

from django.core.exceptions import ValidationError

from MindBridge.models import Problem, Answer, Comment
from .moderation import contains_bad_words, clean_text


# =========================================================
# PROBLEM MODERATION (SOFT MODE - NO CRASH)
# =========================================================
@receiver(pre_save, sender=Problem)
def moderate_problem(sender, instance, **kwargs):
    if contains_bad_words(instance.title) or contains_bad_words(instance.description):
        instance.is_flagged = True
        instance.moderation_note = "Your post contains inappropriate language"


# =========================================================
# ANSWER MODERATION (CLEAN + FLAG)
# =========================================================

@receiver(pre_save, sender=Answer)
def moderate_answer(sender, instance, **kwargs):
    if contains_bad_words(instance.content):
        instance.is_flagged = True
        instance.moderation_note = "Your answer contains inappropriate language"

# =========================================================
# COMMENT MODERATION (CLEAN + FLAG)
# =========================================================
@receiver(pre_save, sender=Comment)
def moderate_comment(sender, instance, **kwargs):

    if contains_bad_words(instance.content):
        instance.is_flagged = True
        instance.moderation_note = "Your comment contains inappropriate language"