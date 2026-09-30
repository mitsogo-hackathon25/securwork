from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=200, blank=True)
    vat_number = models.CharField(max_length=50, blank=True, help_text="P.IVA")

    def __str__(self):
        return self.user.get_username()
