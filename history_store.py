"""생성 당시의 명단과 다운로드 파일을 함께 보관합니다."""

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def connect():
    path = Path(os.environ.get('GSOLD_HISTORY_DB', Path(__file__).parent / '.data' / 'history.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute('''CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, label TEXT NOT NULL,
        created_at TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
        total_workers INTEGER NOT NULL, roster TEXT NOT NULL,
        excel BLOB NOT NULL, png BLOB NOT NULL
    )''')
    connection.commit()
    return connection


def save_report(roster, start, end, title, total_workers, excel, png):
    roster_json = roster.to_json(orient='split', force_ascii=False)
    identity = json.dumps([start.isoformat(), end.isoformat(), total_workers, roster_json],
                          ensure_ascii=False)
    report_id = hashlib.sha256(identity.encode()).hexdigest()
    label = start.strftime('%y.%m.%d')
    if end != start:
        label += '~' + end.strftime('%m.%d' if start.year == end.year else '%y.%m.%d')
    label += ' 고령자 혈압측정'
    connection = connect()
    try:
        with connection:
            connection.execute('''INSERT OR IGNORE INTO reports
                (id, title, label, created_at, start_date, end_date, total_workers, roster, excel, png)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                report_id, title, label, datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
                start.isoformat(), end.isoformat(), int(total_workers), roster_json,
                excel.getvalue(), png.getvalue(),
            ))
    finally:
        connection.close()
    return report_id


def list_reports():
    connection = connect()
    try:
        return [dict(row) for row in connection.execute(
            'SELECT id, title, label, created_at FROM reports ORDER BY created_at DESC, id')]
    finally:
        connection.close()


def load_report(report_id):
    connection = connect()
    try:
        row = connection.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()
