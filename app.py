"""
Smartphone Usage Analyzer - Flask Backend
WITH User Authentication + Admin Panel + Optimized ML
"""

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import pandas as pd
import numpy as np
import joblib
import json
import os
import sqlite3
from datetime import datetime
import secrets
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.preprocessor import UniversalPreprocessor
from utils.suggestions import get_risk_level, generate_suggestions
from utils.auth import (
    init_auth_db, register_user, login_user,
    get_user_from_session, get_all_users, get_user_by_id,
    update_user_predictions, toggle_user_status, delete_user,
    get_login_attempts, get_admin_stats,
    login_required, admin_required
)
from train_model import train_model, generate_sample_dataset

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app)


# ============ DATABASE SETUP ============

def init_db():
    """Initialize all database tables"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT NOT NULL,
            input_data TEXT NOT NULL,
            prediction TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            risk_score REAL NOT NULL,
            model_name TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT NOT NULL,
            screen_time REAL DEFAULT 0,
            social_media REAL DEFAULT 0,
            gaming REAL DEFAULT 0,
            productivity REAL DEFAULT 0,
            app_opens INTEGER DEFAULT 0,
            notifications INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

    # Initialize auth tables
    init_auth_db()


init_db()


def save_prediction(user_id, input_data, prediction, risk_level, risk_score, model_name):
    """Save prediction to database"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO predictions (user_id, timestamp, input_data, prediction, risk_level, risk_score, model_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        datetime.now().isoformat(),
        json.dumps(input_data),
        str(prediction),
        risk_level,
        risk_score,
        model_name
    ))
    conn.commit()
    conn.close()

    # Update user prediction count
    update_user_predictions(user_id)


def save_usage_history(user_id, data):
    """Save daily usage data"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO usage_history (user_id, date, screen_time, social_media, gaming, productivity, app_opens, notifications)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        datetime.now().strftime('%Y-%m-%d'),
        data.get('screen_time', 0),
        data.get('social_media', 0),
        data.get('gaming', 0),
        data.get('productivity', 0),
        data.get('app_opens', 0),
        data.get('notifications', 0)
    ))
    conn.commit()
    conn.close()


# ============ LOAD MODEL ============

def load_model():
    """Load trained model and preprocessor"""
    model = None
    preprocessor = None
    model_info = None

    if os.path.exists('model.pkl') and os.path.exists('preprocessor.pkl'):
        model = joblib.load('model.pkl')
        preprocessor = UniversalPreprocessor.load('preprocessor.pkl')

        if os.path.exists('model_info.json'):
            with open('model_info.json', 'r') as f:
                model_info = json.load(f)

    return model, preprocessor, model_info


# Initial training
if not os.path.exists('model.pkl'):
    print("[INFO] No model found. Training new model...")
    if not os.path.exists('dataset.csv'):
        generate_sample_dataset()
    train_model(dataset_path='dataset.csv')


# ============ AUTH ROUTES ============

@app.route('/login')
def login_page():
    """Login page"""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_page'))
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/register')
def register_page():
    """Registration page"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/admin')
@admin_required
def admin_page():
    """Admin dashboard page"""
    return render_template('admin.html')


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """API: Register new user"""
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    result = register_user(
        username=data.get('username', ''),
        email=data.get('email', ''),
        password=data.get('password', ''),
        full_name=data.get('full_name', '')
    )

    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API: Login user"""
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    ip_address = request.remote_addr
    result = login_user(
        username=data.get('username', ''),
        password=data.get('password', ''),
        ip_address=ip_address
    )

    if result['success']:
        # Set session
        user = result['user']
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['full_name'] = user['full_name']
        session['role'] = user['role']
        session['session_token'] = result['session_token']

        # Determine redirect based on role
        redirect_url = '/admin' if user['role'] == 'admin' else '/'
        result['redirect'] = redirect_url

        return jsonify(result)

    return jsonify(result), 401


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """API: Logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@app.route('/api/auth/me', methods=['GET'])
def api_me():
    """API: Get current user info"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'logged_in': False})

    user = get_user_from_session(session)
    if user:
        return jsonify({
            'success': True,
            'logged_in': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role'],
                'total_predictions': user['total_predictions'],
                'created_at': user['created_at'],
                'last_login': user['last_login']
            }
        })

    session.clear()
    return jsonify({'success': False, 'logged_in': False})


# ============ MAIN ROUTES ============

@app.route('/')
@login_required
def index():
    """Main app page - requires login"""
    return render_template('index.html')


@app.route('/api/model-info', methods=['GET'])
@login_required
def get_model_info():
    """Get current model information"""
    _, _, model_info = load_model()
    if model_info:
        return jsonify({'success': True, 'model_info': model_info})
    return jsonify({'success': False, 'message': 'No model trained yet'})


@app.route('/api/features', methods=['GET'])
@login_required
def get_features():
    """Get required input features"""
    _, preprocessor, _ = load_model()

    if preprocessor and preprocessor.feature_columns:
        features = []
        for col in preprocessor.feature_columns:
            col_type = preprocessor.column_types.get(col, 'numeric')
            features.append({
                'name': col,
                'display_name': col.replace('_', ' ').title(),
                'type': 'number' if col_type == 'numeric' else 'text',
                'step': '0.1' if col_type == 'numeric' else None
            })
        return jsonify({
            'success': True,
            'features': features,
            'target': preprocessor.target_column
        })

    return jsonify({'success': False, 'message': 'Model not trained.'})


@app.route('/api/predict', methods=['POST'])
@login_required
def predict():
    """Make prediction"""
    try:
        model, preprocessor, model_info = load_model()

        if model is None or preprocessor is None:
            return jsonify({
                'success': False,
                'message': 'Model not trained. Upload dataset and train first.'
            }), 400

        input_data = request.json
        if not input_data:
            return jsonify({'success': False, 'message': 'No input data'}), 400

        # Clean data
        clean_data = {}
        for key, value in input_data.items():
            if key in preprocessor.feature_columns:
                clean_data[key] = value

        for col in preprocessor.feature_columns:
            if col not in clean_data:
                if preprocessor.column_types.get(col) == 'numeric':
                    clean_data[col] = 0
                else:
                    clean_data[col] = 'Unknown'

        # Preprocess
        X_input = preprocessor.transform(clean_data)

        # Predict
        prediction = model.predict(X_input)[0]

        # Probabilities
        probabilities = []
        if hasattr(model, 'predict_proba'):
            try:
                proba = model.predict_proba(X_input)[0]
                probabilities = proba.tolist()
            except Exception:
                probabilities = []

        prediction_label = preprocessor.get_target_label(prediction)
        risk_info = get_risk_level(prediction_label, probabilities)
        suggestions = generate_suggestions(risk_info['level'], clean_data)

        # Save
        user_id = session.get('user_id')
        save_prediction(
            user_id,
            clean_data,
            prediction_label,
            risk_info['level'],
            risk_info['score'],
            model_info.get('model_name', 'Unknown') if model_info else 'Unknown'
        )

        # Save usage history
        usage_data = {
            'screen_time': 0, 'social_media': 0, 'gaming': 0,
            'productivity': 0, 'app_opens': 0, 'notifications': 0
        }
        for key, value in clean_data.items():
            key_lower = key.lower()
            try:
                val = float(value)
            except (ValueError, TypeError):
                continue
            if 'screen' in key_lower and 'time' in key_lower:
                usage_data['screen_time'] = val
            elif 'social' in key_lower:
                usage_data['social_media'] = val
            elif 'gaming' in key_lower or 'game' in key_lower:
                usage_data['gaming'] = val
            elif 'productive' in key_lower or 'productivity' in key_lower:
                usage_data['productivity'] = val
            elif 'app' in key_lower and 'open' in key_lower:
                usage_data['app_opens'] = int(val)
            elif 'notification' in key_lower:
                usage_data['notifications'] = int(val)

        save_usage_history(user_id, usage_data)

        response = {
            'success': True,
            'prediction': prediction_label,
            'risk': risk_info,
            'suggestions': suggestions,
            'probabilities': {
                'values': probabilities,
                'labels': []
            },
            'input_summary': clean_data
        }

        if probabilities and '__target__' in preprocessor.label_encoders:
            response['probabilities']['labels'] = list(
                preprocessor.label_encoders['__target__'].classes_
            )

        return jsonify(response)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Prediction error: {str(e)}'
        }), 500


@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Get prediction history for current user"""
    try:
        user_id = session.get('user_id')
        limit = request.args.get('limit', 50, type=int)

        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            'SELECT * FROM predictions WHERE user_id = ? ORDER BY id DESC LIMIT ?',
            (user_id, limit)
        )
        rows = c.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'input_data': json.loads(row['input_data']),
                'prediction': row['prediction'],
                'risk_level': row['risk_level'],
                'risk_score': row['risk_score'],
                'model_name': row['model_name']
            })

        return jsonify({'success': True, 'history': history, 'total': len(history)})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/usage-history', methods=['GET'])
@login_required
def get_usage_history():
    """Get usage history for charts"""
    try:
        user_id = session.get('user_id')
        days = request.args.get('days', 30, type=int)

        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            'SELECT * FROM usage_history WHERE user_id = ? ORDER BY date DESC LIMIT ?',
            (user_id, days)
        )
        rows = c.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                'date': row['date'],
                'screen_time': row['screen_time'],
                'social_media': row['social_media'],
                'gaming': row['gaming'],
                'productivity': row['productivity'],
                'app_opens': row['app_opens'],
                'notifications': row['notifications']
            })

        history.reverse()
        return jsonify({'success': True, 'history': history})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """Get user's statistics"""
    try:
        user_id = session.get('user_id')
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM predictions WHERE user_id = ?', (user_id,))
        total_predictions = c.fetchone()[0]

        c.execute(
            'SELECT risk_level, COUNT(*) FROM predictions WHERE user_id = ? GROUP BY risk_level',
            (user_id,)
        )
        risk_dist = dict(c.fetchall())

        c.execute('SELECT AVG(risk_score) FROM predictions WHERE user_id = ?', (user_id,))
        avg_risk = c.fetchone()[0] or 0

        c.execute(
            'SELECT AVG(screen_time), AVG(social_media), AVG(gaming), AVG(productivity) FROM usage_history WHERE user_id = ?',
            (user_id,)
        )
        avg_usage = c.fetchone()

        conn.close()

        return jsonify({
            'success': True,
            'stats': {
                'total_predictions': total_predictions,
                'risk_distribution': risk_dist,
                'average_risk_score': round(avg_risk, 1),
                'average_usage': {
                    'screen_time': round(avg_usage[0] or 0, 1),
                    'social_media': round(avg_usage[1] or 0, 1),
                    'gaming': round(avg_usage[2] or 0, 1),
                    'productivity': round(avg_usage[3] or 0, 1)
                }
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/train', methods=['POST'])
@login_required
def retrain_model():
    """Retrain model with uploaded dataset"""
    try:
        if 'dataset' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400

        file = request.files['dataset']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        filepath = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(filepath)

        target_column = request.form.get('target_column', None)

        model, preprocessor, model_info = train_model(
            dataset_path=filepath,
            target_column=target_column
        )

        return jsonify({
            'success': True,
            'message': 'Model trained successfully!',
            'model_info': model_info
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Training error: {str(e)}'
        }), 500


@app.route('/api/clear-history', methods=['DELETE'])
@login_required
def clear_history():
    """Clear current user's history"""
    try:
        user_id = session.get('user_id')
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('DELETE FROM predictions WHERE user_id = ?', (user_id,))
        c.execute('DELETE FROM usage_history WHERE user_id = ?', (user_id,))
        c.execute('UPDATE users SET total_predictions = 0 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'History cleared'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ ADMIN API ROUTES ============

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    """Get admin dashboard statistics"""
    stats = get_admin_stats()
    return jsonify({'success': True, 'stats': stats})


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    """Get all users"""
    users = get_all_users()
    return jsonify({'success': True, 'users': users})


@app.route('/api/admin/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_user(user_id):
    """Activate/Deactivate a user"""
    result = toggle_user_status(user_id)
    return jsonify(result)


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """Delete a user"""
    result = delete_user(user_id)
    return jsonify(result)


@app.route('/api/admin/predictions', methods=['GET'])
@admin_required
def admin_get_all_predictions():
    """Get all predictions from all users"""
    try:
        limit = request.args.get('limit', 100, type=int)
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT p.*, u.username, u.full_name
            FROM predictions p
            LEFT JOIN users u ON p.user_id = u.id
            ORDER BY p.id DESC LIMIT ?
        ''', (limit,))
        rows = c.fetchall()
        conn.close()

        predictions = []
        for row in rows:
            predictions.append({
                'id': row['id'],
                'username': row['username'] or 'Unknown',
                'full_name': row['full_name'] or 'Unknown',
                'timestamp': row['timestamp'],
                'prediction': row['prediction'],
                'risk_level': row['risk_level'],
                'risk_score': row['risk_score'],
                'model_name': row['model_name']
            })

        return jsonify({'success': True, 'predictions': predictions})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/login-attempts', methods=['GET'])
@admin_required
def admin_login_attempts():
    """Get login attempts"""
    attempts = get_login_attempts(100)
    return jsonify({'success': True, 'attempts': attempts})


@app.route('/api/admin/clear-all', methods=['DELETE'])
@admin_required
def admin_clear_all():
    """Clear all data (admin only)"""
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('DELETE FROM predictions')
        c.execute('DELETE FROM usage_history')
        c.execute('UPDATE users SET total_predictions = 0')
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'All data cleared'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ RUN ============

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  📱 SMARTPHONE USAGE ANALYZER")
    print("  🔐 With User Auth + Admin Panel")
    print("  🌐 http://localhost:5000")
    print("  👤 Admin: keval/2383, nisarg/1610")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)