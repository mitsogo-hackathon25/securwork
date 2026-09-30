from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Accounts"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save

        User = get_user_model()

        def create_profile(sender, instance, created, **kwargs):
            if created:
                from .models import UserProfile
                UserProfile.objects.get_or_create(user=instance)

        post_save.connect(create_profile, sender=User)
