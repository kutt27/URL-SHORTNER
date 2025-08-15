from django.apps import AppConfig


class ShortenerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shortener'
    verbose_name = 'URL Shortener'
    
    def ready(self):
        # Import signals if any
        pass
