from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    # This app's migrations were created with 32-bit ids (Django 5.2's default); Django 6 defaults to
    # BigAutoField, which would otherwise make makemigrations want to alter every id column.
    default_auto_field = 'django.db.models.AutoField'
    name = 'apps.notifications'
