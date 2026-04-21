"""
Authentication & Authorization System
- User registration with hashed passwords
- User login with session management
- Admin system with pre-seeded accounts
- Role-based access control
"""

import sqlite3
import bcrypt
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, jsonify, request


DB_PATH = 'database.db'


def init_auth_db():
    """Initialize authentication tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            last_login TEXT,
            total_predictions INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            ip_address TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            ip_address TEXT,
            success INTEGER NOT NULL,
            attempted_at TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    seed_admins()


def seed_admins():
    """Create pre-defined admin accounts"""
    admins = [
        {'username': 'keval', 'email': 'keval@admin.com', 'password': '2383',
         'full_name': 'Keval (Admin)', 'role': 'admin'},
        {'username': 'nisarg', 'email': 'nisarg@admin.com', 'password': '1610',
         'full_name': 'Nisarg (Admin)', 'role': 'admin'}
    ]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for admin in admins:
        c.execute('SELECT id FROM users WHERE username = ?', (admin['username'],))
        if c.fetchone() is None:
            password_hash = bcrypt.hashpw(
                admin['password'].encode('utf-8'), bcrypt.gensalt()
            ).decode('utf-8')
            c.execute('''
                INSERT INTO users (username, email, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (admin['username'], admin['email'], password_hash,
                  admin['full_name'], admin['role'], datetime.now().isoformat()))
            print(f"[AUTH] Admin account created: {admin['username']}")
        else:
            password_hash = bcrypt.hashpw(
                admin['password'].encode('utf-8'), bcrypt.gensalt()
            ).decode('utf-8')
            c.execute('UPDATE users SET password_hash = ? WHERE username = ?',
                      (password_hash, admin['username']))

    conn.commit()
    conn.close()


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def register_user(username, email, password, full_name=''):
    """Register a new user"""
    if not username or not email or not password:
        return {'success': False, 'message': 'All fields are required'}
    if len(username) < 3:
        return {'success': False, 'message': 'Username must be at least 3 characters'}
    if len(password) < 4:
        return {'success': False, 'message': 'Password must be at least 4 characters'}
    if '@' not in email:
        return {'success': False, 'message': 'Invalid email address'}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        c.execute('SELECT id FROM users WHERE username = ?', (username.lower(),))
        if c.fetchone():
            conn.close()
            return {'success': False, 'message': 'Username already exists'}

        c.execute('SELECT id FROM users WHERE email = ?', (email.lower(),))
        if c.fetchone():
            conn.close()
            return {'success': False, 'message': 'Email already registered'}

        password_hash = hash_password(password)
        c.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, 'user', ?)
        ''', (username.lower(), email.lower(), password_hash,
              full_name or username, datetime.now().isoformat()))

        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return {'success': True, 'message': 'Registration successful!', 'user_id': user_id}

    except sqlite3.IntegrityError:
        conn.close()
        return {'success': False, 'message': 'Username or email already exists'}
    except Exception as e:
        conn.close()
        return {'success': False, 'message': f'Registration error: {str(e)}'}


def login_user(username, password, ip_address=''):
    """Authenticate a user and create session"""
    if not username or not password:
        return {'success': False, 'message': 'Username and password required'}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        c.execute('SELECT * FROM users WHERE username = ? OR email = ?',
                  (username.lower(), username.lower()))
        user = c.fetchone()

        if not user:
            log_login_attempt(username, ip_address, False)
            conn.close()
            return {'success': False, 'message': 'Invalid username or password'}

        if not user['is_active']:
            conn.close()
            return {'success': False, 'message': 'Account is deactivated. Contact admin.'}

        if not verify_password(password, user['password_hash']):
            log_login_attempt(username, ip_address, False)
            conn.close()
            return {'success': False, 'message': 'Invalid username or password'}

        session_token = secrets.token_hex(32)
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()

        c.execute('''
            INSERT INTO user_sessions (user_id, session_token, created_at, expires_at, ip_address)
            VALUES (?, ?, ?, ?, ?)
        ''', (user['id'], session_token, datetime.now().isoformat(), expires_at, ip_address))

        c.execute('UPDATE users SET last_login = ? WHERE id = ?',
                  (datetime.now().isoformat(), user['id']))

        conn.commit()
        log_login_attempt(username, ip_address, True)
        conn.close()

        return {
            'success': True,
            'message': 'Login successful!',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role']
            },
            'session_token': session_token
        }

    except Exception as e:
        conn.close()
        return {'success': False, 'message': f'Login error: {str(e)}'}


def log_login_attempt(username, ip_address, success):
    """Log login attempts for security"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO login_attempts (username, ip_address, success, attempted_at)
            VALUES (?, ?, ?, ?)
        ''', (username, ip_address, 1 if success else 0, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_user_from_session(session_data):
    """Get user from Flask session"""
    user_id = session_data.get('user_id')
    if not user_id:
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None


def get_all_users():
    """Get all users (admin function)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT id, username, email, full_name, role, is_active,
                 created_at, last_login, total_predictions
                 FROM users ORDER BY created_at DESC''')
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return users


def get_user_by_id(user_id):
    """Get single user by ID"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None


def update_user_predictions(user_id):
    """Increment user's prediction count"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE users SET total_predictions = total_predictions + 1 WHERE id = ?',
                  (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass


def toggle_user_status(user_id):
    """Activate/Deactivate a user"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT is_active, role FROM users WHERE id = ?', (user_id,))
    result = c.fetchone()

    if not result:
        conn.close()
        return {'success': False, 'message': 'User not found'}

    if result[1] == 'admin':
        conn.close()
        return {'success': False, 'message': 'Cannot deactivate admin accounts'}

    new_status = 0 if result[0] else 1
    c.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
    conn.commit()
    conn.close()

    return {
        'success': True,
        'message': f'User {"activated" if new_status else "deactivated"} successfully',
        'is_active': new_status
    }


def delete_user(user_id):
    """Delete a user (admin only)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
    result = c.fetchone()

    if not result:
        conn.close()
        return {'success': False, 'message': 'User not found'}

    if result[0] == 'admin':
        conn.close()
        return {'success': False, 'message': 'Cannot delete admin accounts'}

    c.execute('DELETE FROM predictions WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    return {'success': True, 'message': 'User deleted successfully'}


def get_login_attempts(limit=100):
    """Get recent login attempts (admin function)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM login_attempts ORDER BY attempted_at DESC LIMIT ?', (limit,))
    attempts = [dict(row) for row in c.fetchall()]
    conn.close()
    return attempts


def get_admin_stats():
    """Get statistics for admin dashboard"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM users WHERE role = "user"')
    total_users = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM users WHERE role = "user" AND is_active = 1')
    active_users = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    total_admins = c.fetchone()[0]

    try:
        c.execute('SELECT COUNT(*) FROM predictions')
        total_predictions = c.fetchone()[0]
    except sqlite3.OperationalError:
        total_predictions = 0

    today = datetime.now().strftime('%Y-%m-%d')
    try:
        c.execute('SELECT COUNT(*) FROM predictions WHERE timestamp LIKE ?', (f'{today}%',))
        today_predictions = c.fetchone()[0]
    except sqlite3.OperationalError:
        today_predictions = 0

    try:
        c.execute('SELECT risk_level, COUNT(*) FROM predictions GROUP BY risk_level')
        risk_dist = dict(c.fetchall())
    except sqlite3.OperationalError:
        risk_dist = {}

    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute('SELECT COUNT(*) FROM users WHERE created_at > ? AND role = "user"', (week_ago,))
    recent_signups = c.fetchone()[0]

    c.execute('''
        SELECT username, full_name, total_predictions
        FROM users WHERE role = "user"
        ORDER BY total_predictions DESC LIMIT 10
    ''')
    top_users = [{'username': r[0], 'full_name': r[1], 'predictions': r[2]}
                 for r in c.fetchall()]

    c.execute('SELECT COUNT(*) FROM login_attempts WHERE success = 0 AND attempted_at LIKE ?',
              (f'{today}%',))
    failed_logins_today = c.fetchone()[0]

    conn.close()

    return {
        'total_users': total_users,
        'active_users': active_users,
        'total_admins': total_admins,
        'total_predictions': total_predictions,
        'today_predictions': today_predictions,
        'risk_distribution': risk_dist,
        'recent_signups': recent_signups,
        'top_users': top_users,
        'failed_logins_today': failed_logins_today
    }


# ===== DECORATORS =====

def login_required(f):
    """Decorator: Require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'message': 'Login required',
                    'redirect': '/login'
                }), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator: Require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'message': 'Login required',
                    'redirect': '/login'
                }), 401
            return redirect(url_for('login_page'))

        if session.get('role') != 'admin':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'message': 'Admin access required'
                }), 403
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function