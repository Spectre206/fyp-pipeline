"""
Django Settings — HITL Dashboard

This file contains all Django configuration for the HITL Dashboard application.
Key settings include:

  - INSTALLED_APPS: includes the hitl app and django.channels for SSE support
  - DATABASES: SQLite database stored at layer3/sqlite_logger/decisions.db
  - ALLOWED_HOSTS: set to ['192.168.18.103', 'gateway-node', 'localhost']
    for cluster access
  - CHANNEL_LAYERS: configured for in-memory channel layer (sufficient for
    single-node SSE — no Redis required)
  - DEBUG: True for development/evaluation. Review before any external deployment.
  - SECRET_KEY: loaded from environment variable or .env file (never hardcoded)
  - Static files configuration for the dashboard CSS/JS assets
"""
