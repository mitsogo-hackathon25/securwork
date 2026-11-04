"""Gunicorn settings (Docker / manual start). Matches deploy/systemd/securwork.service."""
bind = "0.0.0.0:8000"
workers = 2
timeout = 600
graceful_timeout = 600
accesslog = "-"
errorlog = "-"
