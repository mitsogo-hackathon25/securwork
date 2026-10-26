"""SQLite pragmas for local dev (concurrent admin import + deletes)."""

from django.db.backends.signals import connection_created


def enable_sqlite_wal() -> None:
    def configure(connection, **kwargs):
        if connection.vendor != "sqlite":
            return
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")

    connection_created.connect(configure, dispatch_uid="securwork_sqlite_wal")
