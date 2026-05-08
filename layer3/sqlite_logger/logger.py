"""
SQLite Decision Logger — Centralised Write Module

This module provides the write interface to the decisions SQLite database.
It is used by both the HITL Dashboard (via the Django ORM model) and the
Auto-Execution Engine (via direct sqlite3 connection, since the executor
runs outside the Django app context).

The logger handles all database writes atomically to prevent partial records
in the event of a crash mid-execution. It exposes a single write_decision()
function that accepts a dictionary matching the decisions table schema and
handles column mapping, JSON serialisation of list fields (original_actions,
final_actions), and timestamp formatting.

The database file path is loaded from an environment variable or defaults to
the path configured in Django settings.py. Both the Django ORM and this direct
writer use the same file — they do not conflict because SQLite handles
concurrent writers via WAL (Write-Ahead Logging) mode.
"""
