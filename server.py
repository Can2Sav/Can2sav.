#!/usr/bin/env python3
import json
import os
import uuid
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / 'data.json'

DB_TYPE = os.getenv('DB_TYPE', '').lower()

MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'can2sav'),
    'charset': 'utf8mb4',
    'use_unicode': True,
}

POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', os.getenv('DB_HOST', '127.0.0.1')),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'user': os.getenv('POSTGRES_USER', os.getenv('DB_USER', 'postgres')),
    'password': os.getenv('POSTGRES_PASSWORD', os.getenv('DB_PASSWORD', '')),
    'dbname': os.getenv('POSTGRES_DATABASE', os.getenv('DB_DATABASE', 'can2sav')),
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
        { 'id': 1, 'group': 'A', 'home': 'Algerie',        'away': 'DOM-TOM',       'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Lun 22 juin', 'time': '19h00' },
        { 'id': 2, 'group': 'A', 'home': "Côte d'Ivoire",  'away': 'Nigeria',        'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Lun 22 juin', 'time': '19h00' },
        { 'id': 3, 'group': 'B', 'home': 'RD Congo',       'away': 'Afrique du Sud', 'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Lun 22 juin', 'time': '20h00' },
        { 'id': 4, 'group': 'B', 'home': 'Cap Vert',       'away': 'Togo',           'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Lun 22 juin', 'time': '20h00' },
        { 'id': 5, 'group': 'C', 'home': 'Senegal',        'away': 'Palestine',      'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Mar 23 juin', 'time': '19h00' },
        { 'id': 6, 'group': 'C', 'home': 'Congo',          'away': 'Tunisie',        'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Mar 23 juin', 'time': '19h00' },
        { 'id': 7, 'group': 'D', 'home': 'Comores',        'away': 'Mali',           'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Mar 23 juin', 'time': '20h00' },
        { 'id': 8, 'group': 'D', 'home': 'Cameroun',       'away': 'Maroc',          'scoreH': None, 'scoreA': None, 'status': 'upcoming', 'date': 'Mar 23 juin', 'time': '20h00' },
    ],
    'teamsEffectif': {}
}

USE_MYSQL = False
MYSQL_ERROR = None
USE_POSTGRES = False
POSTGRES_ERROR = None

try:
    import mysql.connector
    from mysql.connector import errorcode
    USE_MYSQL = True
except ModuleNotFoundError:
    USE_MYSQL = False

try:
    import psycopg2
    import psycopg2.extras
    USE_POSTGRES = True
except ModuleNotFoundError:
    USE_POSTGRES = False


def get_mysql_connection(use_database=True):
    cfg = {
        'host': MYSQL_CONFIG['host'],
        'port': MYSQL_CONFIG['port'],
        'user': MYSQL_CONFIG['user'],
        'password': MYSQL_CONFIG['password'],
        'charset': MYSQL_CONFIG['charset'],
        'use_unicode': MYSQL_CONFIG['use_unicode'],
    }
    if use_database:
        cfg['database'] = MYSQL_CONFIG['database']
    return mysql.connector.connect(**cfg)


def get_postgres_connection():
    return psycopg2.connect(
        host=POSTGRES_CONFIG['host'],
        port=POSTGRES_CONFIG['port'],
        user=POSTGRES_CONFIG['user'],
        password=POSTGRES_CONFIG['password'],
        dbname=POSTGRES_CONFIG['dbname'],
    )


def init_mysql():
    global USE_MYSQL, MYSQL_ERROR
    if not USE_MYSQL:
        MYSQL_ERROR = 'mysql.connector module not installed'
        return False
    try:
        conn = get_mysql_connection(use_database=False)
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{MYSQL_CONFIG['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        cursor.close()
        conn.close()

        conn = get_mysql_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute("""
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
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_effectif (
                team_name VARCHAR(255) PRIMARY KEY,
                effectif INT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except mysql.connector.Error as exc:
        USE_MYSQL = False
        MYSQL_ERROR = str(exc)
        return False


def init_postgres():
    global USE_POSTGRES, POSTGRES_ERROR
    if not USE_POSTGRES:
        POSTGRES_ERROR = 'psycopg2 module not installed'
        return False
    try:
        conn = get_postgres_connection()
        conn.autocommit = True
        cursor = conn.cursor()

        # Supprime les anciennes tables pour repartir proprement
        cursor.execute('DROP TABLE IF EXISTS matches')
        cursor.execute('DROP TABLE IF EXISTS team_effectif')

        # Recrée les tables avec les bonnes colonnes en minuscules
        cursor.execute("""
            CREATE TABLE matches (
                id BIGINT PRIMARY KEY,
                group_name VARCHAR(10),
                home VARCHAR(255),
                away VARCHAR(255),
                scoreh INT NULL,
                scorea INT NULL,
                status VARCHAR(50),
                date_label VARCHAR(100),
                time_label VARCHAR(100)
            )
        """)
        cursor.execute("""
            CREATE TABLE team_effectif (
                team_name VARCHAR(255) PRIMARY KEY,
                effectif INT NOT NULL
            )
        """)
        cursor.close()
        conn.close()
        return True
    except Exception as exc:
        USE_POSTGRES = False
        POSTGRES_ERROR = str(exc)
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
            'id':     int(row['id']),
            'group':  row['group_name'],
            'home':   row['home'],
            'away':   row['away'],
            'scoreH': row['scoreH'],   # MySQL conserve la casse
            'scoreA': row['scoreA'],
            'status': row['status'],
            'date':   row['date_label'],
            'time':   row['time_label'],
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
            item.get('scoreH'),   # ← majuscule : correspond au JSON envoyé par le JS
            item.get('scoreA'),   # ← majuscule
            item.get('status'),
            item.get('date'),
            item.get('time'),
        )
        for item in payload.get('matches', [])
    ]
    if match_values:
        cursor.executemany(insert_match, match_values)
    eff_values = [(team, int(v)) for team, v in payload.get('teamsEffectif', {}).items()]
    if eff_values:
        cursor.executemany('INSERT INTO team_effectif (team_name, effectif) VALUES (%s, %s)', eff_values)
    conn.commit()
    cursor.close()
    conn.close()


def load_data_postgres():
    conn = get_postgres_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute('SELECT * FROM matches ORDER BY id')
    rows = cursor.fetchall()
    cursor.execute('SELECT * FROM team_effectif')
    effectifs = cursor.fetchall()
    cursor.close()
    conn.close()
    matches = [
        {
            'id':     int(row['id']),
            'group':  row['group_name'],
            'home':   row['home'],
            'away':   row['away'],
            'scoreH': row['scoreh'],   # ← minuscule : PostgreSQL convertit toujours en minuscules
            'scoreA': row['scorea'],   # ← minuscule
            'status': row['status'],
            'date':   row['date_label'],
            'time':   row['time_label'],
        }
        for row in rows
    ]
    teams_effectif = {row['team_name']: row['effectif'] for row in effectifs}
    return {'matches': matches, 'teamsEffectif': teams_effectif}


def save_data_postgres(payload):
    conn = get_postgres_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM matches')
    cursor.execute('DELETE FROM team_effectif')
    insert_match = (
        'INSERT INTO matches (id, group_name, home, away, scoreh, scorea, status, date_label, time_label) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)'
    )
    match_values = [
        (
            int(item['id']),
            item.get('group'),
            item.get('home'),
            item.get('away'),
            item.get('scoreH'),   # ← lit 'scoreH' depuis le JSON du JS
            item.get('scoreA'),   # ← lit 'scoreA' depuis le JSON du JS
            item.get('status'),
            item.get('date'),
            item.get('time'),
        )
        for item in payload.get('matches', [])
    ]
    if match_values:
        cursor.executemany(insert_match, match_values)
    eff_values = [(team, int(v)) for team, v in payload.get('teamsEffectif', {}).items()]
    if eff_values:
        cursor.executemany('INSERT INTO team_effectif (team_name, effectif) VALUES (%s, %s)', eff_values)
    conn.commit()
    cursor.close()
    conn.close()


def init_database():
    active = None
    if DB_TYPE in ('postgres', 'postgresql'):
        if init_postgres():
            active = 'postgres'
        elif USE_MYSQL and init_mysql():
            active = 'mysql'
    elif DB_TYPE in ('mysql',):
        if USE_MYSQL and init_mysql():
            active = 'mysql'
        elif USE_POSTGRES and init_postgres():
            active = 'postgres'
    else:
        if USE_POSTGRES and init_postgres():
            active = 'postgres'
        elif USE_MYSQL and init_mysql():
            active = 'mysql'

    if active is None and USE_POSTGRES and init_postgres():
        active = 'postgres'
    if active is None and USE_MYSQL and init_mysql():
        active = 'mysql'
    return active


ACTIVE_DB = None


class Handler(SimpleHTTPRequestHandler):
    def _set_json_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def load_data(self):
        if ACTIVE_DB == 'mysql':
            try:
                return load_data_mysql()
            except Exception as exc:
                print('MySQL load error:', exc, flush=True)
        if ACTIVE_DB == 'postgres':
            try:
                return load_data_postgres()
            except Exception as exc:
                print('Postgres load error:', exc, flush=True)
        if not DATA_FILE.exists():
            DATA_FILE.write_text(json.dumps(DEFAULT_DATA, ensure_ascii=False, indent=2), encoding='utf-8')
        try:
            return json.loads(DATA_FILE.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            DATA_FILE.write_text(json.dumps(DEFAULT_DATA, ensure_ascii=False, indent=2), encoding='utf-8')
            return DEFAULT_DATA.copy()

    def save_data(self, payload):
        if ACTIVE_DB == 'mysql':
            try:
                save_data_mysql(payload)
                print('Saved data to MySQL: matches=', len(payload.get('matches', [])), 'teamsEffectif=', len(payload.get('teamsEffectif', {})), flush=True)
                return
            except Exception as exc:
                print('MySQL save error:', exc, flush=True)
        if ACTIVE_DB == 'postgres':
            try:
                save_data_postgres(payload)
                print('Saved data to Postgres: matches=', len(payload.get('matches', [])), 'teamsEffectif=', len(payload.get('teamsEffectif', {})), flush=True)
                return
            except Exception as exc:
                print('Postgres save error:', exc, flush=True)
        DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Saved data to JSON:', DATA_FILE, flush=True)

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
                    print('Admin login success', flush=True)
                    token = generate_token()
                    self._set_json_headers()
                    self.wfile.write(json.dumps({'success': True, 'token': token}, ensure_ascii=False).encode('utf-8'))
                else:
                    print('Admin login failed', flush=True)
                    self._set_json_headers(401)
                    self.wfile.write(json.dumps({'success': False, 'error': 'Unauthorized'}, ensure_ascii=False).encode('utf-8'))
            except Exception as exc:
                print('Admin login error:', exc, flush=True)
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
                print('Save unauthorized: token invalid', flush=True)
                self._set_json_headers(401)
                self.wfile.write(json.dumps({'success': False, 'error': 'Unauthorized'}, ensure_ascii=False).encode('utf-8'))
                return
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            try:
                payload = json.loads(body)
                print('Received save request: matches=', len(payload.get('matches', [])), 'teamsEffectif=', len(payload.get('teamsEffectif', {})), flush=True)
                self.save_data(payload)
                self._set_json_headers()
                self.wfile.write(json.dumps({'success': True}, ensure_ascii=False).encode('utf-8'))
            except Exception as exc:
                print('Save payload error:', exc, flush=True)
                self._set_json_headers(400)
                self.wfile.write(json.dumps({'success': False, 'error': str(exc)}, ensure_ascii=False).encode('utf-8'))
            return
        self.send_error(404, 'Not Found')


if __name__ == '__main__':
    ACTIVE_DB = init_database()
    if ACTIVE_DB == 'mysql':
        print('MySQL storage enabled. Database:', MYSQL_CONFIG['database'], flush=True)
    elif ACTIVE_DB == 'postgres':
        print('Postgres storage enabled. Database:', POSTGRES_CONFIG['dbname'], flush=True)
    else:
        if DB_TYPE:
            print('Requested DB_TYPE=', DB_TYPE, 'but no database backend could be initialized.', flush=True)
        if USE_MYSQL:
            print('MySQL available? yes, error:', MYSQL_ERROR, flush=True)
        else:
            print('MySQL available? no', flush=True)
        if USE_POSTGRES:
            print('Postgres available? yes, error:', POSTGRES_ERROR, flush=True)
        else:
            print('Postgres available? no', flush=True)
        print('Using local JSON fallback in', DATA_FILE, flush=True)
    port = int(os.getenv('PORT', '8000'))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f'Serving on http://0.0.0.0:{port}')
    print(f'Ouvrez votre navigateur sur http://localhost:{port}/index.html')
    server.serve_forever()
