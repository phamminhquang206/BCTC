import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS responses (
                tool TEXT, args TEXT, payload TEXT, fetched_at TEXT,
                PRIMARY KEY(tool,args));
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY, config TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS jobs (
                run_id INTEGER, symbol TEXT, status TEXT DEFAULT 'pending',
                result TEXT, updated_at TEXT, PRIMARY KEY(run_id,symbol));
        ''')
        self.db.commit()

    def cached(self, tool, args):
        with self.lock:
            row = self.db.execute('SELECT * FROM responses WHERE tool=? AND args=?', (tool, encode(args))).fetchone()
        return (json.loads(row['payload']), row['fetched_at']) if row else None

    def save_response(self, tool, args, payload):
        with self.lock, self.db:
            self.db.execute('INSERT OR REPLACE INTO responses VALUES (?,?,?,?)', (tool, encode(args), encode(payload), now()))

    def new_run(self, config, symbols):
        with self.lock, self.db:
            run_id = self.db.execute('INSERT INTO runs(config,created_at) VALUES (?,?)', (encode(config), now())).lastrowid
            self.db.executemany('INSERT INTO jobs(run_id,symbol) VALUES (?,?)', [(run_id, s) for s in dict.fromkeys(symbols)])
        return run_id

    def runs(self):
        with self.lock:
            return [dict(r) for r in self.db.execute('SELECT * FROM runs ORDER BY id DESC')]

    def config(self, run_id):
        with self.lock:
            return json.loads(self.db.execute('SELECT config FROM runs WHERE id=?', (run_id,)).fetchone()[0])

    def jobs(self, run_id):
        with self.lock:
            return [dict(r) for r in self.db.execute('SELECT * FROM jobs WHERE run_id=? ORDER BY symbol', (run_id,))]

    def finish(self, run_id, symbol, status, result):
        with self.lock, self.db:
            self.db.execute('UPDATE jobs SET status=?,result=?,updated_at=? WHERE run_id=? AND symbol=?', (status, encode(result), now(), run_id, symbol))

    def retry_errors(self, run_id):
        with self.lock, self.db:
            self.db.execute("UPDATE jobs SET status='pending' WHERE run_id=? AND status='error'", (run_id,))

    def close(self):
        with self.lock:
            self.db.close()
