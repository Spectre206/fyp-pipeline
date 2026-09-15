"""Durable append evidence plus decision index. No exactly-once claim."""
import base64
import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def raw_record(body):
    if isinstance(body, str):
        body = body.encode('utf-8')
    return {'body_base64': base64.b64encode(body).decode('ascii')}


def new_run(path, run_id, **metadata):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', run_id):
        raise ValueError('Invalid run_id')
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    (path / 'run.json').write_text(json.dumps({'run_id': run_id, 'created_at': utcnow(), **metadata}, indent=2) + '\n')
    return path


class Journal:
    def __init__(self, directory):
        self.path = Path(directory) / 'journal.sqlite3'
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS decisions(event_id TEXT PRIMARY KEY, payload TEXT NOT NULL, confirmed INTEGER NOT NULL DEFAULT 0);
        ''')

    def append(self, kind, payload):
        with self.lock, self.db:
            self.db.execute('INSERT INTO records(kind,payload) VALUES (?,?)', (kind, json.dumps(payload, allow_nan=False)))

    def decision(self, event_id):
        with self.lock:
            row = self.db.execute('SELECT payload,confirmed FROM decisions WHERE event_id=?', (event_id,)).fetchone()
            return (json.loads(row[0]), bool(row[1])) if row else None

    def prepare(self, decision):
        with self.lock, self.db:
            self.db.execute('INSERT INTO decisions(event_id,payload) VALUES (?,?)',
                            (decision['event_id'], json.dumps(decision, allow_nan=False)))

    def confirm(self, decision):
        with self.lock, self.db:
            self.db.execute('UPDATE decisions SET payload=?,confirmed=1 WHERE event_id=?',
                            (json.dumps(decision, allow_nan=False), decision['event_id']))
            self.db.execute('INSERT INTO records(kind,payload) VALUES (?,?)', ('decision', json.dumps(decision, allow_nan=False)))

    def records(self, kind):
        with self.lock:
            return [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM records WHERE kind=? ORDER BY id', (kind,))]

    def export(self):
        with self.lock:
            for kind in ('decision', 'feedback', 'delivery', 'quarantine', 'failure'):
                target = self.path.parent / (kind + '.jsonl')
                with target.open('w') as output:
                    for row in self.records(kind):
                        output.write(json.dumps(row, allow_nan=False) + '\n')

    def close(self):
        with self.lock:
            self.db.close()
