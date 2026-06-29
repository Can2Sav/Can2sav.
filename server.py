#!/usr/bin/env python3
import json
import os
import uuid
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / 'data.json'

DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'can2sav'),
    'charset': 'utf8mb4',
    'use_unicode': True,
}

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Can2Sav176')
ADMIN_TOKENS = {}
TOKEN_TTL = 60 * 60 * 4  # 4 heures

def generate_token():
    token = uuid.uuid4().hex
    ADMIN_TOKENS[token] = time.time()
    return token

def verify_token(token):
    if not token:
        return False
    expires = ADMIN_TOKENS.get(token)
    if not expires:
        return False
    if time.time() > expires + TOKEN_TTL:
        del ADMIN_TOKENS[token]
        return False
    ADMIN_TOKENS[token] = time.time()
    return True

def revoke_token(token):
    if token in ADMIN_TOKENS:
        del ADMIN_TOKENS[token]

DEFAULT_DATA = {
    'matches': [
        { 'id': 1, 'group': 'A', 'home': 'Algerie',      'away': 'DOM-TOM',      'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Lun 22 juin', 'time': '19h00' },
        { 'id': 2, 'group': 'A', 'home': 'Côte d\'Ivoire', 'away': 'Nigeria',      'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Lun 22 juin', 'time': '19h00' },
        { 'id': 3, 'group': 'B', 'home': 'RD Congo',      'away': 'Afrique du Sud','scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Lun 22 juin', 'time': '20h00' },
        { 'id': 4, 'group': 'B', 'home': 'Cap Vert',      'away': 'Togo',         'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Lun 22 juin', 'time': '20h00' },
        { 'id': 5, 'group': 'C', 'home': 'Senegal',       'away': 'Palestine',   'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Mar 23 juin', 'time': '19h00' },
        { 'id': 6, 'group': 'C', 'home': 'Congo',         'away': 'Tunisie',     'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Mar 23 juin', 'time': '19h00' },
        { 'id': 7, 'group': 'D', 'home': 'Comores',       'away': 'Mali',        'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Mar 23 juin', 'time': '20h00' },
        { 'id': 8, 'group': 'D', 'home': 'Cameroun',      'away': 'Maroc',       'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Mar 23 juin', 'time': '20h00' },
    ],
    'teamsEffectif': {}
}

USE_MYSQL = False
MYSQL_ERROR = None

try:
    import mysql.connector
    from mysql.connector import errorcode
    USE_MYSQL = True
except ModuleNotFoundError:
    USE_MYSQL = False


def get_mysql_connection(use_database=True):
    cfg = {
        'host': DB_CONFIG['host'],
        'port': DB_CONFIG['port'],
        'user': DB_CONFIG['user'],
        'password': DB_CONFIG['password'],
        'charset': DB_CONFIG['charset'],
        'use_unicode': DB_CONFIG['use_unicode'],
    }
    if use_database:
        cfg['database'] = DB_CONFIG['database']
    return mysql.connector.connect(**cfg)


def init_mysql():
    global USE_MYSQL, MYSQL_ERROR
    if not USE_MYSQL:
        MYSQL_ERROR = 'mysql.connector module not installed'
        return False
    try:
        conn = get_mysql_connection(use_database=False)
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        cursor.close()
        conn.close()

        conn = get_mysql_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                id BIGINT PRIMARY KEY,
                group_name VARCHAR(10),
                home VARCHAR(255),
                away VARCHAR(255),
                scoreH INT NULL,
                scoreA INT NULL,
                status VARCHAR(50),
                date_label VARCHAR(100),
                time_label VARCHAR(100)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS team_effectif (
                team_name VARCHAR(255) PRIMARY KEY,
                effectif INT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except mysql.connector.Error as exc:
        USE_MYSQL = False
        MYSQL_ERROR = str(exc)
        return False


def load_data_mysql():
    conn = get_mysql_connection(use_database=True)
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM matches ORDER BY id')
    rows = cursor.fetchall()
    cursor.execute('SELECT * FROM team_effectif')
    effectifs = cursor.fetchall()
    cursor.close()
    conn.close()
    matches = [
        {
            'id': int(row['id']),
            'group': row['group_name'],
            'home': row['home'],
            'away': row['away'],
            'scoreH': row['scoreH'],
            'scoreA': row['scoreA'],
            'status': row['status'],
            'date': row['date_label'],
            'time': row['time_label'],
        }
        for row in rows
    ]
    teams_effectif = {row['team_name']: row['effectif'] for row in effectifs}
    return {'matches': matches, 'teamsEffectif': teams_effectif}


def save_data_mysql(payload):
    conn = get_mysql_connection(use_database=True)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM matches')
    cursor.execute('DELETE FROM team_effectif')
    insert_match = (
        'INSERT INTO matches (id, group_name, home, away, scoreH, scoreA, status, date_label, time_label) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)'
    )
    match_values = [
        (
            int(item['id']),
            item.get('group'),
            item.get('home'),
            item.get('away'),
            item.get('scoreH'),
            item.get('scoreA'),
            item.get('status'),
            item.get('date'),
            item.get('time'),
        )
        for item in payload.get('matches', [])
    ]
    if match_values:
        cursor.executemany(insert_match, match_values)
    insert_eff = (
        'INSERT INTO team_effectif (team_name, effectif) VALUES (%s, %s)'
    )
    eff_values = [
        (team, int(value))
        for team, value in payload.get('teamsEffectif', {}).items()
    ]
    if eff_values:
        cursor.executemany(insert_eff, eff_values)
    conn.commit()
    cursor.close()
    conn.close()


class Handler(SimpleHTTPRequestHandler):
    def _set_json_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def load_data(self):
        if USE_MYSQL:
            try:
                return load_data_mysql()
            except Exception as exc:
                print('MySQL load error:', exc)
        if not DATA_FILE.exists():
            DATA_FILE.write_text(json.dumps(DEFAULT_DATA, ensure_ascii=False, indent=2), encoding='utf-8')
        try:
            return json.loads(DATA_FILE.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            DATA_FILE.write_text(json.dumps(DEFAULT_DATA, ensure_ascii=False, indent=2), encoding='utf-8')
            return DEFAULT_DATA.copy()

    def save_data(self, payload):
        if USE_MYSQL:
            try:
                save_data_mysql(payload)
                return
            except Exception as exc:
                print('MySQL save error:', exc)
        DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def do_GET(self):
        if self.path == '/api/data':
            data = self.load_data()
            self._set_json_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            return
        if self.path == '/api/check':
            auth = self.headers.get('Authorization', '')
            token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
            valid = verify_token(token)
            self._set_json_headers(200 if valid else 401)
            self.wfile.write(json.dumps({'valid': valid}, ensure_ascii=False).encode('utf-8'))
            return
        return super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/login':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            try:
                payload = json.loads(body)
                password = payload.get('password', '')
                if password == ADMIN_PASSWORD:
                    token = generate_token()
                    self._set_json_headers()
                    self.wfile.write(json.dumps({'success': True, 'token': token}, ensure_ascii=False).encode('utf-8'))
                else:
                    self._set_json_headers(401)
                    self.wfile.write(json.dumps({'success': False, 'error': 'Unauthorized'}, ensure_ascii=False).encode('utf-8'))
            except Exception as exc:
                self._set_json_headers(400)
                self.wfile.write(json.dumps({'success': False, 'error': str(exc)}, ensure_ascii=False).encode('utf-8'))
            return
        if self.path == '/api/logout':
            auth = self.headers.get('Authorization', '')
            token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
            revoke_token(token)
            self._set_json_headers()
            self.wfile.write(json.dumps({'success': True}, ensure_ascii=False).encode('utf-8'))
            return
        if self.path == '/api/save':
            auth = self.headers.get('Authorization', '')
            token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
            if not verify_token(token):
                self._set_json_headers(401)
                self.wfile.write(json.dumps({'success': False, 'error': 'Unauthorized'}, ensure_ascii=False).encode('utf-8'))
                return
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            try:
                payload = json.loads(body)
                self.save_data(payload)
                self._set_json_headers()
                self.wfile.write(json.dumps({'success': True}, ensure_ascii=False).encode('utf-8'))
            except Exception as exc:
                self._set_json_headers(400)
                self.wfile.write(json.dumps({'success': False, 'error': str(exc)}, ensure_ascii=False).encode('utf-8'))
            return
        self.send_error(404, 'Not Found')


if __name__ == '__main__':
    mysql_started = init_mysql()
    if mysql_started:
        print('MySQL storage enabled. Database:', DB_CONFIG['database'])
    else:
        print('MySQL storage disabled:', MYSQL_ERROR)
        print('Using local JSON fallback in', DATA_FILE)
    port = int(os.getenv('PORT', '8000'))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f'Serving on http://0.0.0.0:{port}')
    print(f'Ouvrez votre navigateur sur http://localhost:{port}/index.html')
    server.serve_forever()
