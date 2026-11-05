import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Ensure username 'admin' exists, is staff/superuser, and set password from "
        "ADMIN_PASSWORD env (or --password)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="",
            help="New password (default: ADMIN_PASSWORD from environment)",
        )
        parser.add_argument(
            "--username",
            default="admin",
            help="Staff admin username (default: admin)",
        )

    def handle(self, *args, **options):
        username = (options["username"] or "admin").strip()
        password = (options["password"] or os.environ.get("ADMIN_PASSWORD") or "").strip()
        if not password:
            self.stderr.write(
                self.style.ERROR(
                    "Set ADMIN_PASSWORD in .env or pass --password.",
                ),
            )
            raise SystemExit(1)

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": "admin@securwork.it",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if not user.email:
            user.email = "admin@securwork.it"
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created staff admin '{username}'."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated password for '{username}'."))
