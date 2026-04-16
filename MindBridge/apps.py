from django.apps import AppConfig


class MindbridgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'MindBridge'

    def ready(self):
        import MindBridge.util.signals