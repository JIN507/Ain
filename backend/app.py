"""
Flask API for Ain News Monitor
"""
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from models import init_db, get_db, Country, Source, Keyword, Article, User, AuditLog, ExportRecord, UserFile, SearchHistory
import uuid
from rss_service import fetch_all_feeds, fetch_feed
from translation_service import (
    translate_keyword, 
    detect_language, 
    translate_to_arabic, 
    analyze_sentiment
)
# New multilingual services
from keyword_expansion import expand_keyword, get_all_expansions, load_expansions_from_keywords
from multilingual_matcher import match_article_against_keywords, detect_article_language
from translation_cache import translate_article_to_arabic
from arabic_utils import normalize_arabic
from multilingual_monitor import fetch_and_match_multilingual, save_matched_articles
# New optimized async services
from async_monitor_wrapper import run_optimized_monitoring, save_matched_articles_sync
# Utils
from utils import clean_html_content
from datetime import datetime
from functools import wraps
import json
import os
import re

app = Flask(__name__, static_folder='static', static_url_path='')

# Ensure JSON responses use UTF-8 and do not escape Arabic characters
app.config['JSON_AS_ASCII'] = False
try:
    # Flask >= 2.3
    app.json.ensure_ascii = False  # type: ignore[attr-defined]
except Exception:
    pass

# Basic security config (can be overridden via .env)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
if os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true':
    app.config['SESSION_COOKIE_SECURE'] = True

login_manager = LoginManager(app)
csrf = CSRFProtect(app)

# Single-origin deployment: frontend is served by Flask from backend/static
# This keeps behavior identical between local dev (with proxy) and Render.
CORS(app, supports_credentials=True)

# Initialize database on startup
init_db()
try:
    from models import engine as _engine
    print(f"[DB] Connected to database: {_engine.url}")
except Exception:
    pass

# Database session management
@app.teardown_appcontext
def shutdown_session(exception=None):
    """Close database sessions after each request"""
    pass  # Sessions are now managed per-request

def admin_required(fn):
    """Decorator that requires the current user to be an ADMIN."""
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        try:
            print(f"[AUTH] admin_required check: auth={current_user.is_authenticated}, id={getattr(current_user, 'id', None)}, email={getattr(current_user, 'email', None)}, role={getattr(current_user, 'role', None)}")
        except Exception:
            pass
        if getattr(current_user, "role", "USER") != "ADMIN":
            return jsonify({"error": "Forbidden"}), 403
        return fn(*args, **kwargs)

    return wrapper


def scoped(query, Model):
    """Scope queries to the current user for models that have user_id.

    - ADMIN sees all rows.
    - Regular users see only rows where Model.user_id == current_user.id.
    - Anonymous users get the original query (public/global data only).
    """
    try:
        if not current_user.is_authenticated:
            return query
        if getattr(current_user, "role", "USER") == "ADMIN":
            return query
        if hasattr(Model, "user_id"):
            return query.filter(Model.user_id == current_user.id)
        return query
    except RuntimeError:
        # Outside request context; just return original query
        return query


def log_action(user_id=None, admin_id=None, action="", meta=None):
    """Write a simple audit log entry.

    meta can be any JSON-serializable object; it will be stored as JSON text.
    Errors are swallowed so logging never breaks main flows.
    """
    try:
        db = get_db()
        try:
            meta_text = None
            if meta is not None:
                try:
                    meta_text = json.dumps(meta, ensure_ascii=False)
                except Exception:
                    meta_text = str(meta)

            entry = AuditLog(
                user_id=user_id,
                admin_id=admin_id,
                action=action or "",
                meta_json=meta_text,
            )
            db.add(entry)
            db.commit()
        finally:
            db.close()
    except Exception:
        # Never fail the main request because of audit logging
        pass


@app.route('/api/admin/audit', methods=['GET'])
@admin_required
def admin_audit_logs():
    """Return recent audit log entries for admins.

    Optional query params:
      - user_id: filter by user
      - limit: max number of rows (default 50)
    """
    user_id = request.args.get('user_id', type=int)
    limit = request.args.get('limit', default=50, type=int)
    limit = max(1, min(limit, 200))

    db = get_db()
    try:
        query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        logs = query.limit(limit).all()
        result = []
        for row in logs:
            try:
                meta = json.loads(row.meta_json) if row.meta_json else None
            except Exception:
                meta = row.meta_json
            result.append({
                'id': row.id,
                'user_id': row.user_id,
                'admin_id': row.admin_id,
                'action': row.action,
                'meta': meta,
                'created_at': row.created_at.isoformat() if row.created_at else None,
            })
        return jsonify(result)
    finally:
        db.close()


@app.route('/api/exports', methods=['GET'])
@login_required
def list_exports():
    """List export history. Admins see all files, users see only their own."""
    db = get_db()
    try:
        is_admin = current_user.role == 'ADMIN'
        
        if is_admin:
            # Admin sees all exports with user info
            exports = db.query(ExportRecord).order_by(ExportRecord.created_at.desc()).all()
        else:
            # Regular user sees only their exports
            exports = db.query(ExportRecord).filter(
                ExportRecord.user_id == current_user.id
            ).order_by(ExportRecord.created_at.desc()).all()
        
        # Build user lookup for admin view
        user_map = {}
        if is_admin:
            user_ids = set(rec.user_id for rec in exports)
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            user_map = {u.id: u.name for u in users}
        
        result = []
        for rec in exports:
            try:
                filters = json.loads(rec.filters_json) if rec.filters_json else None
            except Exception:
                filters = None
            item = {
                'id': rec.id,
                'article_count': rec.article_count,
                'filters': filters,
                'filename': rec.filename,
                'file_size': rec.file_size,
                'has_file': bool(rec.stored_filename),
                'created_at': rec.created_at.isoformat() if rec.created_at else None,
            }
            if is_admin:
                item['user_id'] = rec.user_id
                item['user_name'] = user_map.get(rec.user_id, 'مستخدم غير معروف')
            result.append(item)
        return jsonify(result)
    finally:
        db.close()


EXPORTS_FOLDER = os.path.join(os.path.dirname(__file__), 'exports')
os.makedirs(EXPORTS_FOLDER, exist_ok=True)

def get_user_exports_folder(user_id):
    """Get or create user-specific exports folder"""
    user_folder = os.path.join(EXPORTS_FOLDER, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder


@app.route('/api/exports', methods=['POST'])
@login_required
@csrf.exempt
def create_export_record():
    """Create an export record for the current user with optional file upload.

    Accepts multipart form data with:
    - file: PDF file (optional)
    - filters: JSON string of filters
    - article_count: number of articles
    """
    # Handle both JSON and multipart form data
    if request.content_type and 'multipart/form-data' in request.content_type:
        filters_str = request.form.get('filters', '{}')
        article_count = int(request.form.get('article_count', 0))
        source_type = request.form.get('source_type', 'dashboard')
        file = request.files.get('file')
        try:
            filters = json.loads(filters_str)
        except:
            filters = {}
    else:
        data = request.get_json() or {}
        filters = data.get('filters') or {}
        article_count = int(data.get('article_count') or 0)
        source_type = data.get('source_type', 'dashboard')
        file = None

    db = get_db()
    try:
        rec = ExportRecord(
            user_id=current_user.id,
            filters_json=json.dumps(filters, ensure_ascii=False) if filters else None,
            article_count=article_count,
            source_type=source_type,
        )
        
        # Handle file upload
        if file and file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'pdf'
            stored_filename = f"{uuid.uuid4().hex}.{ext}"
            user_folder = get_user_exports_folder(current_user.id)
            file_path = os.path.join(user_folder, stored_filename)
            file.save(file_path)
            
            rec.filename = file.filename
            rec.stored_filename = stored_filename
            rec.file_size = os.path.getsize(file_path)
        
        db.add(rec)
        db.commit()
        try:
            log_action(user_id=current_user.id, action="export_pdf", meta={
                'export_id': rec.id,
                'article_count': article_count,
            })
        except Exception:
            pass
        return jsonify({'success': True, 'id': rec.id}), 201
    finally:
        db.close()


@app.route('/api/exports/<int:export_id>/download', methods=['GET'])
@login_required
def download_export(export_id):
    """Download an exported file. Admins can download any file."""
    db = get_db()
    try:
        is_admin = current_user.role == 'ADMIN'
        
        if is_admin:
            # Admin can download any file
            rec = db.query(ExportRecord).filter(ExportRecord.id == export_id).first()
        else:
            # Regular user can only download their own files
            rec = db.query(ExportRecord).filter(
                ExportRecord.id == export_id,
                ExportRecord.user_id == current_user.id
            ).first()
        
        if not rec:
            return jsonify({'error': 'السجل غير موجود'}), 404
        
        if not rec.stored_filename:
            return jsonify({'error': 'لا يوجد ملف مرفق'}), 404
        
        # Use the file owner's folder, not current_user
        user_folder = get_user_exports_folder(rec.user_id)
        file_path = os.path.join(user_folder, rec.stored_filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'الملف غير موجود'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=rec.filename or f"export_{export_id}.pdf"
        )
    finally:
        db.close()


@app.route('/api/exports/<int:export_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_export(export_id):
    """Delete an export record and its file. Admins can delete any file."""
    db = get_db()
    try:
        is_admin = current_user.role == 'ADMIN'
        
        if is_admin:
            rec = db.query(ExportRecord).filter(ExportRecord.id == export_id).first()
        else:
            rec = db.query(ExportRecord).filter(
                ExportRecord.id == export_id,
                ExportRecord.user_id == current_user.id
            ).first()
        
        if not rec:
            return jsonify({'error': 'السجل غير موجود'}), 404
        
        # Delete file if exists - use file owner's folder
        if rec.stored_filename:
            user_folder = get_user_exports_folder(rec.user_id)
            file_path = os.path.join(user_folder, rec.stored_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        db.delete(rec)
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()


# ==================== User Files APIs ====================
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'csv', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_upload_folder(user_id):
    """Get or create user-specific upload folder"""
    user_folder = os.path.join(UPLOAD_FOLDER, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder


@app.route('/api/files', methods=['GET'])
@login_required
def list_user_files():
    """List files for the current user."""
    db = get_db()
    try:
        files = db.query(UserFile).filter(
            UserFile.user_id == current_user.id
        ).order_by(UserFile.created_at.desc()).all()
        result = []
        for f in files:
            result.append({
                'id': f.id,
                'filename': f.filename,
                'file_type': f.file_type,
                'file_size': f.file_size,
                'description': f.description,
                'created_at': f.created_at.isoformat() if f.created_at else None,
            })
        return jsonify(result)
    finally:
        db.close()


@app.route('/api/files', methods=['POST'])
@login_required
@csrf.exempt
def upload_user_file():
    """Upload a file for the current user."""
    if 'file' not in request.files:
        return jsonify({'error': 'لم يتم تحديد ملف'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'لم يتم تحديد ملف'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'نوع الملف غير مسموح'}), 400
    
    # Generate unique stored filename
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    stored_filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    
    # Save file to user folder
    user_folder = get_user_upload_folder(current_user.id)
    file_path = os.path.join(user_folder, stored_filename)
    file.save(file_path)
    
    # Get file size
    file_size = os.path.getsize(file_path)
    
    # Get description from form data
    description = request.form.get('description', '')
    
    db = get_db()
    try:
        user_file = UserFile(
            user_id=current_user.id,
            filename=file.filename,
            stored_filename=stored_filename,
            file_type=ext,
            file_size=file_size,
            description=description,
        )
        db.add(user_file)
        db.commit()
        return jsonify({
            'success': True,
            'id': user_file.id,
            'filename': user_file.filename,
        }), 201
    finally:
        db.close()


@app.route('/api/files/<int:file_id>', methods=['GET'])
@login_required
def download_user_file(file_id):
    """Download a user file."""
    db = get_db()
    try:
        user_file = db.query(UserFile).filter(
            UserFile.id == file_id,
            UserFile.user_id == current_user.id
        ).first()
        if not user_file:
            return jsonify({'error': 'الملف غير موجود'}), 404
        
        user_folder = get_user_upload_folder(current_user.id)
        file_path = os.path.join(user_folder, user_file.stored_filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'الملف غير موجود على الخادم'}), 404
        
        from flask import send_file
        return send_file(
            file_path,
            download_name=user_file.filename,
            as_attachment=True
        )
    finally:
        db.close()


@app.route('/api/files/<int:file_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_user_file(file_id):
    """Delete a user file."""
    db = get_db()
    try:
        user_file = db.query(UserFile).filter(
            UserFile.id == file_id,
            UserFile.user_id == current_user.id
        ).first()
        if not user_file:
            return jsonify({'error': 'الملف غير موجود'}), 404
        
        # Delete physical file
        user_folder = get_user_upload_folder(current_user.id)
        file_path = os.path.join(user_folder, user_file.stored_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete database record
        db.delete(user_file)
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()


# ==================== Search History APIs ====================

@app.route('/api/search-history', methods=['GET'])
@login_required
def list_search_history():
    """List search history for the current user."""
    db = get_db()
    try:
        history = db.query(SearchHistory).filter(
            SearchHistory.user_id == current_user.id
        ).order_by(SearchHistory.created_at.desc()).limit(50).all()
        result = []
        for h in history:
            try:
                filters = json.loads(h.filters_json) if h.filters_json else None
            except Exception:
                filters = None
            result.append({
                'id': h.id,
                'search_type': h.search_type,
                'query': h.query,
                'filters': filters,
                'results_count': h.results_count,
                'created_at': h.created_at.isoformat() if h.created_at else None,
            })
        return jsonify(result)
    finally:
        db.close()


@app.route('/api/search-history', methods=['POST'])
@login_required
@csrf.exempt
def create_search_history():
    """Record a search in history."""
    data = request.get_json() or {}
    search_type = data.get('search_type', 'keyword')
    query = data.get('query', '')
    filters = data.get('filters') or {}
    results_count = int(data.get('results_count') or 0)

    db = get_db()
    try:
        rec = SearchHistory(
            user_id=current_user.id,
            search_type=search_type,
            query=query,
            filters_json=json.dumps(filters, ensure_ascii=False) if filters else None,
            results_count=results_count,
        )
        db.add(rec)
        db.commit()
        return jsonify({'success': True, 'id': rec.id}), 201
    finally:
        db.close()


@app.route('/api/search-history/<int:history_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_search_history(history_id):
    """Delete a search history entry."""
    db = get_db()
    try:
        rec = db.query(SearchHistory).filter(
            SearchHistory.id == history_id,
            SearchHistory.user_id == current_user.id
        ).first()
        if not rec:
            return jsonify({'error': 'السجل غير موجود'}), 404
        db.delete(rec)
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()


# ==================== Admin APIs ====================

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_list_users():
    """List users with optional search by name/email (ADMIN only)."""
    q = (request.args.get('q') or '').strip().lower()
    db = get_db()
    try:
        query = db.query(User)
        if q:
            like = f"%{q}%"
            query = query.filter(
                (User.email.ilike(like)) | (User.name.ilike(like))
            )
        users = query.order_by(User.created_at.desc()).all()
        result = [{
            'id': u.id,
            'name': u.name,
            'email': u.email,
            'role': u.role,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat() if u.created_at else None
        } for u in users]
        return jsonify(result)
    finally:
        db.close()


@app.route('/api/admin/users', methods=['POST'])
@admin_required
@csrf.exempt
def admin_create_user():
    """Create a new user (ADMIN only).

    Expects JSON: {name, email, role?, is_active?, password?}
    """
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    name = (data.get('name') or '').strip()
    role = data.get('role') or 'USER'
    is_active = bool(data.get('is_active', True))
    password = data.get('password') or '0000'

    if not email or not name:
        return jsonify({'error': 'Name and email are required'}), 400

    if role not in ('ADMIN', 'USER'):
        role = 'USER'

    db = get_db()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return jsonify({'error': 'User with this email already exists'}), 400

        from auth_utils import hash_password
        user = User(
            email=email,
            name=name,
            role=role,
            is_active=is_active,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        try:
            log_action(
                admin_id=getattr(current_user, 'id', None),
                user_id=user.id,
                action="admin_create_user",
                meta={"email": email, "role": role}
            )
        except Exception:
            pass

        return jsonify({'success': True, 'id': user.id}), 201
    finally:
        db.close()


@app.route('/api/admin/users/<int:user_id>', methods=['PATCH'])
@admin_required
@csrf.exempt
def admin_update_user(user_id):
    """Update basic user fields (name, role, is_active, optional password reset)."""
    data = request.get_json() or {}
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            new_email = (data.get('email') or '').strip().lower()
            if new_email:
                user.email = new_email
        if 'role' in data and data['role'] in ('ADMIN', 'USER'):
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        from auth_utils import hash_password
        if data.get('reset_password'):
            user.password_hash = hash_password('0000')
        if data.get('password'):
            user.password_hash = hash_password(data['password'])
        db.commit()
        try:
            log_action(
                admin_id=getattr(current_user, 'id', None),
                user_id=user.id,
                action="admin_update_user",
                meta={k: data[k] for k in data.keys() if k != 'password'}
            )
        except Exception:
            pass
        return jsonify({'success': True})
    finally:
        db.close()


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
@csrf.exempt
def admin_delete_user(user_id):
    """Delete a user (ADMIN only)."""
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Optional: prevent admin from deleting themselves
        try:
            if current_user.is_authenticated and current_user.id == user.id:
                return jsonify({'error': 'Cannot delete currently logged-in user'}), 400
        except Exception:
            pass

        db.delete(user)
        db.commit()
        try:
            log_action(
                admin_id=getattr(current_user, 'id', None),
                user_id=user.id,
                action="admin_delete_user",
                meta={"email": user.email}
            )
        except Exception:
            pass
        return jsonify({'success': True})
    finally:
        db.close()


@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    """Basic system statistics for admin dashboard."""
    db = get_db()
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_keywords = db.query(Keyword).count()
        total_articles = db.query(Article).count()
        total_exports = db.query(ExportRecord).count()
        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'total_keywords': total_keywords,
            'total_articles': total_articles,
            'total_exports': total_exports,
        })
    finally:
        db.close()


# Whitelist for authentication (legacy; kept for compatibility)
ALLOWED_EMAILS = ["t09301970@gmail.com"]


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    try:
        return db.query(User).get(int(user_id))
    finally:
        db.close()


@app.route('/')
def index():
    """Serve built frontend from the static folder (backend/static)."""
    return send_from_directory('static', 'index.html')

@app.route('/api/auth/check', methods=['POST'])
def check_auth():
    """Legacy auth check by email whitelist (kept for backward compatibility)."""
    data = request.get_json()
    email = data.get('email', '')
    
    if email in ALLOWED_EMAILS:
        return jsonify({"authorized": True})
    else:
        return jsonify({"authorized": False}), 403


# ==================== Session-based Auth ====================

from auth_utils import hash_password, verify_password


@app.route('/api/auth/signup', methods=['POST'])
@csrf.exempt
def signup():
    """Public signup endpoint.

    Creates an inactive USER that must be approved by an admin (is_active=False).
    Expects JSON: {"name": str, "email": str, "password": str}
    """
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400

    db = get_db()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return jsonify({"error": "User with this email already exists"}), 400

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role='USER',
            is_active=False,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        try:
            log_action(user_id=user.id, action="signup_requested", meta={"email": email})
        except Exception:
            pass

        return jsonify({"success": True, "pending_approval": True}), 201
    finally:
        db.close()


@app.route('/api/auth/login', methods=['POST'])
@csrf.exempt  # CSRF token can be added later from frontend; keep simple for now
def login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    db = get_db()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            return jsonify({"error": "بيانات الدخول غير صحيحة"}), 401
        if not user.is_active:
            return jsonify({"error": "حسابك غير مفعل. يرجى انتظار موافقة الإدارة"}), 403
        login_user(user)
        try:
            print(f"[AUTH] login success: id={user.id}, email={user.email}, role={user.role}")
        except Exception:
            pass
        try:
            log_action(user_id=user.id, action="login")
        except Exception:
            pass
        return jsonify({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        })
    finally:
        db.close()


@app.route('/api/auth/logout', methods=['POST'])
@login_required
@csrf.exempt
def logout():
    uid = getattr(current_user, 'id', None)
    logout_user()
    try:
        if uid:
            log_action(user_id=uid, action="logout")
    except Exception:
        pass
    return jsonify({"success": True})


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    try:
        print(f"[AUTH] /api/auth/me: auth={current_user.is_authenticated}, id={getattr(current_user, 'id', None)}, email={getattr(current_user, 'email', None)}, role={getattr(current_user, 'role', None)}")
    except Exception:
        pass
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role
    })

# ==================== Countries ====================

@app.route('/api/countries', methods=['GET'])
def get_countries():
    """Get all countries"""
    db = get_db()
    try:
        countries = db.query(Country).all()
        
        result = [{
            'id': c.id,
            'name_ar': c.name_ar,
            'enabled': c.enabled
        } for c in countries]
        
        return jsonify(result)
    finally:
        db.close()

@app.route('/api/countries/<int:country_id>/toggle', methods=['POST'])
def toggle_country(country_id):
    """Toggle country enabled status"""
    db = get_db()
    try:
        country = db.query(Country).filter(Country.id == country_id).first()
        
        if not country:
            return jsonify({"error": "Country not found"}), 404
        
        country.enabled = not country.enabled
        db.commit()
        
        return jsonify({"success": True, "enabled": country.enabled})
    finally:
        db.close()

# ==================== Sources ====================

@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Get all sources"""
    db = get_db()
    try:
        sources = db.query(Source).all()
        
        result = [{
            'id': s.id,
            'country_id': s.country_id,
            'country_name': s.country_name,
            'name': s.name,
            'url': s.url,
            'enabled': s.enabled,
            'fail_count': s.fail_count
        } for s in sources]
        
        return jsonify(result)
    finally:
        db.close()

@app.route('/api/sources', methods=['POST'])
@csrf.exempt
def add_source():
    """Add new RSS source"""
    data = request.get_json()
    db = get_db()
    try:
        # Check if URL already exists
        existing = db.query(Source).filter(Source.url == data['url']).first()
        if existing:
            return jsonify({"error": "Source already exists"}), 400
        
        source = Source(
            country_id=data.get('country_id', 0),
            country_name=data['country_name'],
            name=data['name'],
            url=data['url'],
            enabled=True
        )
        
        db.add(source)
        db.commit()
        
        return jsonify({"success": True, "id": source.id})
    finally:
        db.close()

@app.route('/api/sources/<int:source_id>', methods=['PUT'])
@csrf.exempt
def update_source(source_id):
    """Update source"""
    db = get_db()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        
        if not source:
            return jsonify({"error": "Source not found"}), 404
        
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            source.name = data['name']
        if 'url' in data:
            source.url = data['url']
        if 'enabled' in data:
            source.enabled = data['enabled']
        
        db.commit()
        
        return jsonify({"success": True})
    finally:
        db.close()

@app.route('/api/sources/<int:source_id>', methods=['DELETE'])
@csrf.exempt
def delete_source(source_id):
    """Delete source"""
    db = get_db()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        
        if not source:
            return jsonify({"error": "Source not found"}), 404
        
        db.delete(source)
        db.commit()
        
        return jsonify({"success": True})
    finally:
        db.close()

@app.route('/api/sources/<int:source_id>/toggle', methods=['POST'])
def toggle_source(source_id):
    """Toggle source enabled status"""
    db = get_db()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        
        if not source:
            return jsonify({"error": "Source not found"}), 404
        
        source.enabled = not source.enabled
        db.commit()
        
        return jsonify({"success": True, "enabled": source.enabled})
    finally:
        db.close()

# ==================== Keywords ====================

@app.route('/api/keywords', methods=['GET'])
def get_keywords():
    """Get all keywords with translations.

    For authenticated non-admin users, results are scoped to their own keywords.
    Admins see all keywords. Anonymous users see all (legacy behavior).
    """
    db = get_db()
    try:
        query = scoped(db.query(Keyword), Keyword)
        keywords = query.all()
        
        result = [{
            'id': k.id,
            'text_ar': k.text_ar,
            'text_en': k.text_en,
            'text_fr': k.text_fr,
            'text_tr': k.text_tr,
            'text_ur': k.text_ur,
            'text_zh': k.text_zh,
            'text_ru': k.text_ru,
            'text_es': k.text_es,
            'enabled': k.enabled
        } for k in keywords]
        
        return jsonify(result)
    finally:
        db.close()

@app.route('/api/keywords/expanded', methods=['GET'])
def get_keywords_expanded():
    """Get all keywords with their multilingual expansions"""
    db = get_db()
    try:
        # Get all enabled keywords
        keywords = db.query(Keyword).filter(Keyword.enabled == True).all()
        
        # Load/generate expansions for all keywords
        expansions = load_expansions_from_keywords(keywords)
        
        return jsonify(expansions)
    finally:
        db.close()

@app.route('/api/keywords', methods=['POST'])
@login_required
@csrf.exempt
def add_keyword():
    """Add new keyword with auto-translation to 7 languages + expansion"""
    data = request.get_json() or {}
    db = get_db()
    try:
        keyword_ar = (data.get('text_ar') or '').strip()

        if not keyword_ar:
            return jsonify({"error": "النص العربي للكلمة مطلوب"}), 400
        
        # Check if keyword already exists FOR THIS USER only
        existing = scoped(db.query(Keyword), Keyword).filter(Keyword.text_ar == keyword_ar).first()
        if existing:
            return jsonify({"error": "هذه الكلمة موجودة بالفعل لهذا المستخدم"}), 400
        
        # Step 1: Translate keyword using Google Translate to 7 base languages (for DB storage)
        print(f"🔄 Step 1: Translating keyword to 7 base languages: {keyword_ar}")
        translations = translate_keyword(keyword_ar)
        print(f"   ✅ Translated to: en, fr, tr, ur, zh, ru, es")
        
        # Create keyword with all translations
        keyword = Keyword(
            text_ar=keyword_ar,
            text_en=translations.get('en'),
            text_fr=translations.get('fr'),
            text_tr=translations.get('tr'),
            text_ur=translations.get('ur'),
            text_zh=translations.get('zh'),
            text_ru=translations.get('ru'),
            text_es=translations.get('es'),
            enabled=True,
            user_id=getattr(current_user, 'id', None)
        )
        
        db.add(keyword)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            # Handle existing global UNIQUE constraint on keywords.text_ar
            if 'UNIQUE constraint failed: keywords.text_ar' in str(e):
                return jsonify({"error": "هذه الكلمة موجودة مسبقاً في القاموس المشترك للنظام"}), 400
            raise
        
        print(f"   ✅ Keyword saved to database (ID: {keyword.id})")
        
        # Step 2: Expand keyword to 32 languages for comprehensive multilingual matching
        print(f"🔄 Step 2: Expanding keyword to 32 languages for global search...")
        expansion = expand_keyword(keyword_ar)
        
        if expansion['status'] == 'success':
            print(f"   ✅ Expanded successfully to {len(expansion['translations'])} languages")
            print(f"   📋 Coverage: en, fr, es, de, ru, zh-cn, ja, hi, id, pt, tr, ko, it, nl, vi, th, ms, fa, ur, +more")
        elif expansion['status'] == 'partial':
            print(f"   ⚠️  Partially expanded to {len(expansion['translations'])} languages")
        else:
            print(f"   ❌ Expansion failed")
        
        return jsonify({
            "success": True,
            "id": keyword.id,
            "translations": translations,
            "expansion": expansion  # Include expansion in response
        })
    finally:
        db.close()

@app.route('/api/keywords/<int:keyword_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_keyword(keyword_id):
    """Delete keyword"""
    db = get_db()
    try:
        query = scoped(db.query(Keyword), Keyword)
        keyword = query.filter(Keyword.id == keyword_id).first()
        
        if not keyword:
            return jsonify({"error": "Keyword not found"}), 404
        
        db.delete(keyword)
        db.commit()
        
        return jsonify({"success": True})
    finally:
        db.close()

@app.route('/api/keywords/<int:keyword_id>/toggle', methods=['POST'])
@login_required
def toggle_keyword(keyword_id):
    """Toggle keyword enabled status"""
    db = get_db()
    try:
        query = scoped(db.query(Keyword), Keyword)
        keyword = query.filter(Keyword.id == keyword_id).first()
        
        if not keyword:
            return jsonify({"error": "Keyword not found"}), 404
        
        keyword.enabled = not keyword.enabled
        db.commit()
        
        return jsonify({"success": True, "enabled": keyword.enabled})
    finally:
        db.close()

# ==================== Monitoring ====================

@app.route('/api/monitor/run', methods=['POST'])
@csrf.exempt
def run_monitoring():
    """
    Main monitoring function - fetches news and analyzes with Gemini
    This runs on-demand when user clicks the button
    """
    db = get_db()
    
    try:
        # Get ALL enabled sources and keywords (no country bias!)
        sources = db.query(Source).filter(Source.enabled == True).all()
        keywords = db.query(Keyword).filter(Keyword.enabled == True).all()
        
        if not sources:
            return jsonify({"error": "No enabled sources"}), 400
        
        if not keywords:
            return jsonify({"error": "No enabled keywords"}), 400
        
        # Log sources breakdown by country (for transparency)
        print("\n📊 Enabled Sources Breakdown:")
        country_counts = {}
        for s in sources:
            country = s.country_name
            country_counts[country] = country_counts.get(country, 0) + 1
        
        for country, count in sorted(country_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"   • {country}: {count} sources")
        
        if len(country_counts) > 10:
            print(f"   ... and {len(country_counts) - 10} more countries")
        
        print(f"\n✅ Total: {len(sources)} sources from {len(country_counts)} countries")
        print(f"✅ Keywords: {len(keywords)}")
        print(f"🎯 System will fetch from ALL countries equally (no bias!)\n")
        
        # Convert to dicts for processing
        sources_list = [{
            'id': s.id,
            'country_name': s.country_name,
            'name': s.name,
            'url': s.url,
            'enabled': s.enabled
        } for s in sources]
        
        keywords_list = [{
            'id': k.id,
            'text_ar': k.text_ar,
            'text_en': k.text_en,
            'text_fr': k.text_fr,
            'text_tr': k.text_tr,
            'text_ur': k.text_ur,
            'text_zh': k.text_zh,
            'text_ru': k.text_ru,
            'text_es': k.text_es,
            'enabled': k.enabled
        } for k in keywords]
        
        # Step 1: Load CACHED keyword expansions (NEVER translates during monitoring!)
        print("🔄 Loading cached keyword expansions...")
        keyword_expansions = load_expansions_from_keywords(keywords)
        
        if not keyword_expansions:
            print("❌ No cached expansions found!")
            print("   → Please add keywords via frontend first")
            return jsonify({"error": "No cached keyword expansions. Please add keywords first."}), 400
        
        print(f"✅ Loaded {len(keyword_expansions)} cached expansions (no translation needed)")
        print(f"   ⚡ Instant load - expansions were pre-computed when keywords were added\n")
        
        # Step 2: Fetch all feeds CONCURRENTLY and match with keywords (NEW OPTIMIZED!)
        monitoring_result = run_optimized_monitoring(
            sources_list,
            keyword_expansions,
            max_concurrent=50,  # Fetch 50 sources at once!
            max_per_source=30
        )
        
        if not monitoring_result['success'] or not monitoring_result.get('matches'):
            print("⚠️ No matches found")
            return jsonify({    
                "success": True,
                "total_fetched": monitoring_result.get('total_fetched', 0),
                "total_matches": 0,
                "articles": []
            })
        
        matches = monitoring_result['matches']
        
        # Step 3: Save matched articles with multilingual translations
        print(f"\n💾 Saving matched articles with Arabic translations...")
        print("ℹ️ Using Google Translate (FREE) with caching")
        print("ℹ️ Sentiment analysis: Neutral (default)\n")
        
        # Use new save function with balancing (no hard-coded limit!) and per-user ownership
        from flask_login import current_user as _cu
        owner_id = getattr(_cu, 'id', None)
        saved_ids, save_stats = save_matched_articles_sync(
            db,
            matches,
            apply_limit=True,
            user_id=owner_id,
        )
        
        # Retrieve saved articles for response
        processed_articles = []
        if saved_ids:
            saved_articles = db.query(Article).filter(Article.id.in_(saved_ids)).all()
            for a in saved_articles:
                processed_articles.append({
                    'id': a.id,
                    'country': a.country,
                    'source_name': a.source_name,
                    'keyword': a.keyword_original,
                    'title_ar': a.title_ar,
                    'summary_ar': a.summary_ar,
                    'sentiment': a.sentiment_label,
                    'language': a.original_language,
                    'url': a.url,
                    'image_url': a.image_url,
                    'published_at': a.published_at.isoformat() if a.published_at else None
                })
        
        print(f"\n{'='*50}")
        print(f"✅ Monitoring complete!")
        print(f"📊 Saved {len(processed_articles)} new articles")
        print(f"{'='*50}\n")
        
        # Build comprehensive response with all stats
        return jsonify({
            "success": True,
            
            # Fetch statistics
            "total_sources": len(sources_list),
            "successful_sources": len([r for r in monitoring_result.get('fetch_results', []) if r.get('status') == 'success']),
            "total_fetched": monitoring_result.get('total_fetched', 0),
            
            # Match statistics
            "total_matches": len(matches),
            "per_keyword_stats": monitoring_result.get('keyword_stats', {}),
            "acceptance_rate": monitoring_result.get('acceptance_rate', 0),
            
            # Save statistics
            "total_saved": save_stats.get('total_saved', 0),
            "duplicates_skipped": save_stats.get('duplicates_skipped', 0),
            "save_limit_applied": save_stats.get('limit_applied', False),
            "save_limit": save_stats.get('save_limit'),
            "balancing_stats": save_stats.get('balancing_stats'),
            
            # Feed health
            "feed_health": monitoring_result.get('feed_health'),
            
            # Config
            "config": monitoring_result.get('config'),
            
            # Articles
            "articles": processed_articles
        })
    
    except Exception as e:
        print(f"❌ Error in monitoring: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ==================== Articles ====================

@app.route('/api/articles', methods=['GET'])
def get_articles():
    """Get all articles with optional filters"""
    db = get_db()
    try:
        # Get query parameters
        country = request.args.get('country')
        keyword = request.args.get('keyword')
        sentiment = request.args.get('sentiment')
        search = request.args.get('search')
        
        # Base query (scoped per user for privacy)
        query = scoped(db.query(Article), Article).order_by(Article.created_at.desc())
        
        # Apply filters
        if country:
            query = query.filter(Article.country == country)
        if keyword:
            # Use keyword_original (NEW field) instead of keyword (deprecated)
            query = query.filter(Article.keyword_original == keyword)
        if sentiment:
            # Use sentiment_label (NEW field) instead of sentiment (deprecated)
            query = query.filter(Article.sentiment_label == sentiment)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Article.title_ar.like(search_term)) |
                (Article.summary_ar.like(search_term))
            )
        
        # Return all articles (no limit) so we can see all countries
        # If performance becomes an issue, increase limit or add pagination
        articles = query.all()
        
        result = []
        for a in articles:
            # Parse keywords_translations JSON to get match context
            match_context = None
            keyword_original = a.keyword_original or a.keyword
            
            if a.keywords_translations:
                try:
                    keywords_data = json.loads(a.keywords_translations)
                    match_contexts = keywords_data.get('match_contexts', [])
                    # Get context for primary keyword
                    if match_contexts:
                        match_context = match_contexts[0]  # Use first context (primary keyword)
                except:
                    pass  # Ignore JSON parse errors
            
            article_data = {
                'id': a.id,
                'country': a.country,
                'source_name': a.source_name,
                'keyword': keyword_original,
                'keyword_original': keyword_original,
                # Original fields
                'title': a.title_original,
                'summary': a.summary_original,
                'language_detected': a.original_language or 'unknown',
                'image_url': a.image_url,
                # Arabic translations
                'title_ar': a.title_ar,
                'summary_ar': a.summary_ar,
                'translation_status': 'success' if a.title_ar and a.summary_ar else 'partial' if a.title_ar or a.summary_ar else 'none',
                # Match context (NEW - for showing why article matched)
                'match_context': match_context,
                # Other fields
                'sentiment': a.sentiment_label or a.sentiment,
                'url': a.url,
                'published_at': a.published_at.isoformat() if a.published_at else None,
                'created_at': a.created_at.isoformat() if a.created_at else None
            }
            result.append(article_data)
        
        return jsonify(result)
    finally:
        db.close()

@app.route('/api/sources/countries', methods=['GET'])
def get_sources_countries():
    """Get countries from Country table with source count (for Top Headlines)"""
    db = get_db()
    try:
        from sqlalchemy import func
        
        # Get all enabled countries from Country table
        countries = db.query(Country).filter(Country.enabled == True).all()
        
        result = []
        for country in countries:
            # Count sources for this country
            source_count = db.query(Source).filter(
                Source.country_name == country.name_ar,
                Source.enabled == True
            ).count()
            
            # Only include countries that have sources
            if source_count > 0:
                result.append({
                    'name': country.name_ar,
                    'count': source_count
                })
        
        # Sort by source count descending
        result.sort(key=lambda x: x['count'], reverse=True)
        
        # Log for debugging
        if result:
            print(f"📰 Found {len(result)} countries with sources:")
            for c in result:
                print(f"   • {c['name']}: {c['count']} sources")
        
        return jsonify({'countries': result})
    finally:
        db.close()


@app.route('/api/articles/countries', methods=['GET'])
def get_articles_countries():
    """Get distinct countries from actual articles (not Country table)"""
    db = get_db()
    try:
        # Get distinct countries from articles that actually exist
        from sqlalchemy import distinct, func
        
        countries_query = db.query(
            Article.country,
            func.count(Article.id).label('article_count')
        ).group_by(Article.country).order_by(func.count(Article.id).desc())
        
        result = []
        for country, count in countries_query:
            if country:  # Skip None/empty
                result.append({
                    'name_ar': country,
                    'article_count': count
                })
        
        # Log for debugging
        if result:
            print(f"📊 Found {len(result)} countries with articles:")
            for c in result:
                print(f"   • {c['name_ar']}: {c['article_count']} articles")
        
        return jsonify(result)
    finally:
        db.close()

@app.route('/api/health/translation', methods=['GET'])
def health_check_translation():
    """Test Google Translate service (no API key needed)"""
    try:
        from googletrans import Translator
        translator = Translator()
        
        # Quick test: translate "hello" to Arabic
        result = translator.translate("hello", src='en', dest='ar')
        
        if result and result.text:
            return jsonify({
                "ok": True,
                "service": "Google Translate",
                "test": f"hello → {result.text}",
                "status": "FREE - No API key required"
            })
        else:
            return jsonify({
                "ok": False,
                "error": "No response from Google Translate"
            }), 500
            
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500

@app.route('/api/articles/stats', methods=['GET'])
def get_article_stats():
    """Get article statistics"""
    db = get_db()
    try:
        total = db.query(Article).count()
        
        # Count using Arabic sentiment labels (check both new and old columns)
        from sqlalchemy import or_
        
        positive = db.query(Article).filter(
            or_(
                Article.sentiment_label == 'إيجابي',
                Article.sentiment == 'إيجابي'
            )
        ).count()
        
        negative = db.query(Article).filter(
            or_(
                Article.sentiment_label == 'سلبي',
                Article.sentiment == 'سلبي'
            )
        ).count()
        
        neutral = db.query(Article).filter(
            or_(
                Article.sentiment_label == 'محايد',
                Article.sentiment == 'محايد'
            )
        ).count()
        
        return jsonify({
            'total': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral
        })
    finally:
        db.close()

@app.route('/api/articles/clear', methods=['POST'])
def clear_articles():
    """Clear all articles"""
    db = get_db()
    try:
        db.query(Article).delete()
        db.commit()
        
        return jsonify({"success": True})
    finally:
        db.close()

@app.route('/api/articles/export-and-reset', methods=['POST'])
@login_required
@csrf.exempt
def export_and_reset():
    """
    Export all articles to Excel, then delete all articles and keywords
    Atomic operation: all or nothing
    """
    import openpyxl
    from openpyxl.styles import Font, Alignment
    from datetime import datetime as dt
    import os
    
    db = get_db()
    export_path = None
    
    try:
        # Step 1: Fetch all articles
        print("📊 Fetching all articles for export...")
        articles = db.query(Article).order_by(Article.created_at.desc()).all()
        article_count = len(articles)
        
        if article_count == 0:
            return jsonify({"error": "No articles to export"}), 400
        
        print(f"   ✅ Found {article_count} articles")
        
        # Step 2: Create Excel file
        timestamp = dt.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"export_{timestamp}.xlsx"
        export_path = os.path.join(os.getcwd(), 'exports', filename)
        
        # Create exports directory if it doesn't exist
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        
        print(f"📝 Creating Excel file: {filename}")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "articles"
        
        # Headers - matching spec exactly
        headers = [
            'id', 'title_original', 'title_ar', 'source', 'country', 'url', 
            'published_at_utc', 'original_language', 'arabic_text', 
            'keyword_original', 'keywords_translations', 'sentiment_label', 
            'sentiment_score', 'fetched_at_utc'
        ]
        
        # Style headers
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # Write article data
        for row_idx, article in enumerate(articles, 2):
            ws.cell(row=row_idx, column=1, value=article.id)
            ws.cell(row=row_idx, column=2, value=article.title_original or '')
            ws.cell(row=row_idx, column=3, value=article.title_ar or '')
            ws.cell(row=row_idx, column=4, value=article.source_name)
            ws.cell(row=row_idx, column=5, value=article.country)
            ws.cell(row=row_idx, column=6, value=article.url)
            ws.cell(row=row_idx, column=7, value=article.published_at.isoformat() if article.published_at else '')
            ws.cell(row=row_idx, column=8, value=article.original_language or article.language or '')
            ws.cell(row=row_idx, column=9, value=article.arabic_text or (article.title_ar + ' ' + (article.summary_ar or '')))
            ws.cell(row=row_idx, column=10, value=article.keyword_original or article.keyword or '')
            ws.cell(row=row_idx, column=11, value=article.keywords_translations or '')
            ws.cell(row=row_idx, column=12, value=article.sentiment_label or article.sentiment or '')
            ws.cell(row=row_idx, column=13, value=article.sentiment_score or '')
            ws.cell(row=row_idx, column=14, value=article.fetched_at.isoformat() if article.fetched_at else article.created_at.isoformat())
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save workbook
        wb.save(export_path)
        print(f"   ✅ Excel file saved: {export_path}")
        
        # Step 3: Verify export
        wb_verify = openpyxl.load_workbook(export_path)
        ws_verify = wb_verify.active
        exported_rows = ws_verify.max_row - 1  # Minus header row
        wb_verify.close()
        
        if exported_rows != article_count:
            raise Exception(f"Export verification failed: expected {article_count} rows, got {exported_rows}")
        
        print(f"   ✅ Export verified: {exported_rows} rows")
        
        # Step 4: Delete all data (atomic transaction)
        print("🗑️ Starting atomic delete transaction...")
        
        # Delete in single transaction
        db.query(Article).delete()
        db.query(Keyword).delete()
        db.commit()
        
        print("   ✅ All data deleted from database")
        
        # Step 5: Clear in-memory caches
        from translation_service import clear_all_caches
        clear_all_caches()
        
        # Step 6: Return success with download link
        return jsonify({
            "success": True,
            "filename": filename,
            "article_count": article_count,
            "download_url": f"/api/exports/download/{filename}"
        })
        
    except Exception as e:
        print(f"❌ Export & Reset failed: {str(e)}")
        db.rollback()
        
        # Clean up partial export file
        if export_path and os.path.exists(export_path):
            try:
                os.remove(export_path)
                print("   🧹 Cleaned up partial export file")
            except:
                pass
        
        return jsonify({"error": f"Export failed: {str(e)}"}), 500
        
    finally:
        db.close()

# ==================== Diagnostics ====================

@app.route('/api/feeds/diagnose', methods=['GET'])
def diagnose_feeds():
    """
    Diagnose all feeds - check their status and errors
    Returns detailed status for each feed
    """
    db = get_db()
    try:
        # Get limit from query params (0 = all)
        limit = int(request.args.get('limit', '0'))
        
        # Get all sources or limited set
        query = db.query(Source).order_by(Source.country_name, Source.name)
        if limit > 0:
            query = query.limit(limit)
        sources = query.all()
        
        results = []
        count = 0
        
        print(f"\n{'='*50}")
        print(f"🔍 Diagnosing {len(sources)} feeds...")
        print(f"{'='*50}\n")
        
        for source in sources:
            print(f"Testing: {source.name} ({source.country_name})")
            
            result = fetch_feed(source.url)
            
            results.append({
                "country": source.country_name,
                "source": source.name,
                "url": source.url,
                "enabled": source.enabled,
                "status": result["status"],
                "http_status": result["http_status"],
                "entries_count": len(result["entries"]),
                "error": result["error"]
            })
            
            count += 1
            
            # Small delay between tests
            import time
            time.sleep(0.3)
        
        print(f"\n{'='*50}")
        print(f"✅ Diagnosis complete!")
        print(f"{'='*50}\n")
        
        return jsonify({
            "success": True,
            "total_tested": count,
            "feeds": results
        })
    finally:
        db.close()

@app.route('/api/feeds/selftest', methods=['GET'])
def selftest_feeds():
    """
    Quick self-test - test first N enabled feeds
    Returns summary of working vs failing feeds
    """
    db = get_db()
    try:
        # Get limit from query params (default 5)
        limit = int(request.args.get('limit', '5'))
        
        # Get first N enabled sources
        sources = db.query(Source).filter(Source.enabled == True).limit(limit).all()
        
        if not sources:
            return jsonify({
                "success": False,
                "error": "No enabled sources found"
            }), 400
        
        results = []
        working = 0
        failing = 0
        
        print(f"\n{'='*50}")
        print(f"🧪 Self-test: Testing {len(sources)} feeds...")
        print(f"{'='*50}\n")
        
        for source in sources:
            print(f"Testing: {source.name}")
            
            result = fetch_feed(source.url)
            
            is_ok = result["status"] == "ok" and len(result["entries"]) > 0
            
            if is_ok:
                working += 1
                print(f"   ✅ OK - {len(result['entries'])} entries")
            else:
                failing += 1
                print(f"   ❌ {result['status']} - {result['error']}")
            
            results.append({
                "source": source.name,
                "country": source.country_name,
                "status": result["status"],
                "entries": len(result["entries"]),
                "ok": is_ok
            })
            
            import time
            time.sleep(0.3)
        
        print(f"\n{'='*50}")
        print(f"✅ Self-test complete!")
        print(f"   Working: {working}/{len(sources)}")
        print(f"   Failing: {failing}/{len(sources)}")
        print(f"{'='*50}\n")
        
        return jsonify({
            "success": True,
            "total_tested": len(sources),
            "working": working,
            "failing": failing,
            "feeds": results
        })
    finally:
        db.close()


def calculate_relevance_score(article_data, keywords):
    """
    Calculate relevance score (0-1) for an article based on keyword presence
    
    Args:
        article_data: Dict with 'title', 'description', 'content' fields
        keywords: List of keyword variants (Arabic + English)
    
    Returns:
        Float score (0-1), higher = more relevant
    """
    title = (article_data.get('title') or '').lower()
    description = (article_data.get('description') or article_data.get('content') or '').lower()
    
    # Normalize keywords for matching
    keywords_lower = [k.lower() for k in keywords if k]
    
    score = 0.0
    matches_found = False
    
    # Check title (weight: 0.6)
    for kw in keywords_lower:
        if kw in title:
            # Title match is most important
            # Count occurrences (more = better, but capped at 3)
            occurrences = min(title.count(kw), 3)
            score += 0.6 * (occurrences / 3.0)
            matches_found = True
            break  # One match in title is enough
    
    # Check description/content (weight: 0.4)
    for kw in keywords_lower:
        if kw in description:
            # Count occurrences in description
            occurrences = min(description.count(kw), 5)
            score += 0.4 * (occurrences / 5.0)
            matches_found = True
            break
    
    # If no matches at all, score = 0
    if not matches_found:
        return 0.0
    
    # Normalize score to 0-1 range
    return min(score, 1.0)


from flask import request, jsonify
import os
import requests
from datetime import datetime as dt

@app.route('/api/direct-search', methods=['GET'])
def direct_search():
    """
    Simple NewsData.io direct search:
    - Query params: q, qInTitle, timeframe, country, language, page
    - Single API call (no caching, no translation, no scoring)
    - Returns normalized results in الخلاصة-style format
    """

    API_KEY = os.getenv('NEWSDATA_API_KEY', '').strip()
    BASE_URL = 'https://newsdata.io/api/1/latest'

    # --- Basic validation ---
    keyword   = (request.args.get('q', '') or '').strip()
    next_page = (request.args.get('page', '') or '').strip()

    if not keyword and not next_page:
        return jsonify({
            "error": "الرجاء إدخال كلمة البحث",
            "results": [],
            "nextPage": None,
            "totalResults": 0
        }), 400

    if not API_KEY:
        return jsonify({
            "error": "مفتاح API غير موجود أو غير صحيح - يرجى إضافة NEWSDATA_API_KEY في ملف .env",
            "results": [],
            "nextPage": None,
            "totalResults": 0
        }), 500

    # --- Build API params (recommended simple usage) ---
    params = {"apikey": API_KEY}

    if next_page:
        # Pagination: فقط نرسل page + apikey
        params["page"] = next_page
    else:
        q_in_title = (request.args.get('qInTitle', '') or '').lower() == 'true'
        timeframe  = (request.args.get('timeframe', '') or '').strip()
        country    = (request.args.get('country', '') or '').strip()
        language   = (request.args.get('language', '') or '').strip()

        # Either q or qInTitle (كما هو موصى به)
        if q_in_title:
            params["qInTitle"] = keyword
        else:
            params["q"] = keyword

        if timeframe:
            params["timeframe"] = timeframe

        if country:
            # NewsData.io تسمح حتى 5 دول فقط
            params["country"] = ",".join(country.split(",")[:5])

        if language:
            params["language"] = language

    # --- Call NewsData.io once ---
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
    except requests.RequestException as e:
        return jsonify({
            "error": f"خطأ في الاتصال بواجهة NewsData.io: {str(e)[:200]}",
            "results": [],
            "nextPage": None,
            "totalResults": 0
        }), 200

    # --- Parse response safely ---
    try:
        data = response.json()
    except ValueError:
        return jsonify({
            "error": "خطأ في تحليل استجابة NewsData.io",
            "results": [],
            "nextPage": None,
            "totalResults": 0
        }), 200

    if response.status_code != 200 or data.get("status") != "success":
        return jsonify({
            "error": data.get("message", "فشل البحث من NewsData.io"),
            "results": [],
            "nextPage": None,
            "totalResults": 0
        }), 200

    raw_results = data.get("results", []) or []

    # --- Normalize to your الخلاصة format (بدون ترجمة أو فلترة معقدة) ---
    results = []
    for idx, article in enumerate(raw_results):
        title = (article.get("title") or "").strip()
        description = (article.get("description") or article.get("content") or "").strip()
        url = article.get("link", "")

        # تجاهل المقالات الناقصة
        if not title or not url:
            continue

        result = {
            "id": hash(url) if url else idx,
            "title_ar": title,            # بدون ترجمة – فقط تمرير العنوان كما هو
            "title_original": title,
            "summary_ar": description,    # بدون ترجمة – الوصف كما هو
            "summary_original": description,
            "url": url,
            "source_name": article.get("source_name") or article.get("source_id", "Unknown"),
            "country": article.get("country"),          # قد تكون list أو كود دولة
            "language_detected": article.get("language"),
            "published_at": article.get("pubDate"),
            "image_url": article.get("image_url"),
            "keyword_original": keyword if not next_page else "",
            "sentiment": "محايد",
            "created_at": dt.now().isoformat(),
            "is_newsdata": True
        }

        results.append(result)

    # --- Final response ---
    return jsonify({
        "results": results,
        "nextPage": data.get("nextPage"),
        "totalResults": len(results)
    }), 200



@app.route('/api/headlines/top', methods=['GET'])
def get_top_headlines():
    """
    Get top headlines from all sources in a country
    Query params: country (required), per_source (default 5), translate (default true)
    """
    from googletrans import Translator
    import feedparser
    from datetime import datetime as dt
    from time import mktime
    import uuid
    
    # Simple in-memory cache (60-120s TTL)
    cache_key = None
    cache_ttl = 90  # 90 seconds
    
    if not hasattr(get_top_headlines, 'cache'):
        get_top_headlines.cache = {}
    
    try:
        # Generate request ID for clearer logging
        req_id = str(uuid.uuid4())[:8]
        
        # Get params
        country_name = request.args.get('country', '').strip()
        per_source = int(request.args.get('per_source', 5))
        translate = request.args.get('translate', 'true').lower() == 'true'
        
        if not country_name:
            return jsonify({"error": "الرجاء تحديد الدولة"}), 400
        
        # Check cache
        cache_key = f"{country_name}_{per_source}_{translate}"
        if cache_key in get_top_headlines.cache:
            cached_data, cached_time = get_top_headlines.cache[cache_key]
            if (dt.now() - cached_time).total_seconds() < cache_ttl:
                print(f"[{req_id}] ✅ Cache hit for {country_name}")
                return jsonify(cached_data)
        
        print(f"[{req_id}] 🔍 Fetching top headlines for: {country_name}")
        
        # Get sources from database
        db = get_db()
        try:
            sources = db.query(Source).filter(Source.country_name == country_name).all()
            
            if not sources:
                return jsonify({"error": f"لا توجد مصادر للدولة: {country_name}"}), 404
            
            print(f"[{req_id}] Found {len(sources)} sources for {country_name}")
            
            # Fetch headlines from each source
            results = []
            translator = Translator() if translate else None
            
            for source in sources:
                source_result = {
                    'source_name': source.name,
                    'source_url': source.url,
                    'articles': [],
                    'error': None
                }
                
                try:
                    print(f"[{req_id}] 📡 {source.name}")
                    
                    # Parse RSS feed with timeout
                    import socket
                    old_timeout = socket.getdefaulttimeout()
                    socket.setdefaulttimeout(10)
                    
                    try:
                        # feedparser.parse() doesn't accept timeout parameter
                        feed = feedparser.parse(source.url)
                    except socket.timeout:
                        source_result['error'] = 'انتهت المهلة (timeout)'
                        results.append(source_result)
                        continue
                    finally:
                        socket.setdefaulttimeout(old_timeout)
                    
                    if not feed.entries:
                        source_result['error'] = 'لا توجد أخبار'
                        results.append(source_result)
                        continue
                    
                    # Sort by date (newest first) and take top N
                    entries = feed.entries[:per_source * 2]  # Fetch extra in case of issues
                    
                    # Sort by published date
                    def get_date(entry):
                        try:
                            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                return mktime(entry.published_parsed)
                            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                                return mktime(entry.updated_parsed)
                            else:
                                return 0
                        except:
                            return 0
                    
                    entries.sort(key=get_date, reverse=True)
                    entries = entries[:per_source]
                    
                    # Process entries
                    for entry in entries:
                        title = entry.get('title', '')
                        summary_raw = entry.get('summary', '') or entry.get('description', '')
                        url = entry.get('link', '')
                        
                        if not title or not url:
                            continue
                        
                        # Clean HTML from summary (remove ads, navigation, social links, etc.)
                        summary = clean_html_content(summary_raw) if summary_raw else ''
                        
                        # Get published date
                        pub_date = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            pub_date = dt.fromtimestamp(mktime(entry.published_parsed)).isoformat()
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            pub_date = dt.fromtimestamp(mktime(entry.updated_parsed)).isoformat()
                        
                        # Translate if needed
                        title_ar = title
                        summary_ar = summary
                        
                        if translate and translator:
                            try:
                                # Detect language
                                lang = 'en'
                                try:
                                    from langdetect import detect
                                    lang = detect(title)
                                except:
                                    pass
                                
                                if lang != 'ar':
                                    # Translate title
                                    if title:
                                        trans = translator.translate(title, src=lang, dest='ar')
                                        title_ar = trans.text if trans else title
                                    
                                    # Translate summary (limit length)
                                    if summary:
                                        trans = translator.translate(summary[:500], src=lang, dest='ar')
                                        summary_ar = trans.text if trans else summary
                            except Exception as trans_err:
                                print(f"      Translation error: {trans_err}")
                                # Keep original if translation fails
                                pass
                        
                        # Build article object
                        article = {
                            'id': hash(url),
                            'title_ar': title_ar,
                            'title_original': title,
                            'summary_ar': summary_ar,
                            'summary_original': summary,
                            'url': url,
                            'published_at': pub_date,
                            'sentiment': 'محايد',
                            'keyword_original': '',  # No keyword for top headlines
                        }
                        
                        source_result['articles'].append(article)
                    
                    if len(source_result['articles']) > 0:
                        print(f"[{req_id}]    ✅ {len(source_result['articles'])} articles")
                    
                except Exception as source_err:
                    print(f"[{req_id}]    ❌ Error: {source_err}")
                    source_result['error'] = str(source_err)[:100]
                
                results.append(source_result)
            
            # Filter out sources with no articles
            results = [r for r in results if len(r['articles']) > 0 or r['error']]
            
            response_data = {
                'country': country_name,
                'sources': results,
                'total_sources': len(results),
                'total_articles': sum(len(r['articles']) for r in results)
            }
            
            # Update cache
            get_top_headlines.cache[cache_key] = (response_data, dt.now())
            
            # Clean old cache entries (keep only last 10)
            if len(get_top_headlines.cache) > 10:
                oldest_key = min(get_top_headlines.cache.keys(), 
                               key=lambda k: get_top_headlines.cache[k][1])
                del get_top_headlines.cache[oldest_key]
            
            print(f"[{req_id}] ✅ {country_name}: {response_data['total_articles']} articles from {response_data['total_sources']} sources")

            # Return the response data
            return jsonify(response_data)

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Error in get_top_headlines: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/external/headlines', methods=['POST'])
@csrf.exempt
def external_headlines():
    """External API: Get top headlines (أهم العناوين) for a given country.

    - Method: POST
    - Auth: X-API-Key header OR ?api_key=... query param
    - Body (JSON): {"country": "اسم الدولة بالعربية", "per_source": 5, "translate": true}

    Response JSON has the same structure as /api/headlines/top:
    {
      "country": "...",
      "sources": [
        {
          "source_name": "...",
          "source_url": "...",
          "articles": [ ... ],
          "error": null | "..."
        }
      ],
      "total_sources": N,
      "total_articles": M
    }
    """

    from googletrans import Translator
    import feedparser
    from datetime import datetime as dt
    from time import mktime
    import socket

    # ---------- Authentication ----------
    external_key = os.getenv('EXTERNAL_API_KEY', '').strip()
    if not external_key:
        return jsonify({
            "error": "EXTERNAL_API_KEY is not configured on the server",
            "code": "config_error"
        }), 500

    provided_key = (request.headers.get('X-API-Key') or '').strip() or \
                   (request.args.get('api_key', '') or '').strip()

    if not provided_key or provided_key != external_key:
        return jsonify({
            "error": "Unauthorized",
            "code": "unauthorized"
        }), 401

    # ---------- Input validation ----------
    try:
        payload = request.get_json(force=True, silent=False) or {}
    except Exception:
        return jsonify({
            "error": "Invalid JSON body",
            "code": "bad_request"
        }), 400

    country_name = (payload.get('country') or '').strip()
    if not country_name:
        return jsonify({
            "error": "Field 'country' is required",
            "code": "missing_country"
        }), 400

    try:
        per_source = int(payload.get('per_source') or 5)
    except Exception:
        per_source = 5

    translate = bool(payload.get('translate', True))

    # ---------- Core logic (similar to get_top_headlines, no cache) ----------
    db = get_db()
    try:
        # First, resolve the country row by its Arabic name
        from models import Country as _Country
        country_row = db.query(_Country).filter(_Country.name_ar == country_name).first()

        if not country_row:
            return jsonify({
                "error": f"لا توجد مصادر للدولة: {country_name}",
                "code": "no_sources"
            }), 404

        # Then fetch all sources linked to this country_id
        sources = db.query(Source).filter(Source.country_id == country_row.id).all()

        if not sources:
            return jsonify({
                "error": f"لا توجد مصادر للدولة: {country_name}",
                "code": "no_sources"
            }), 404

        results = []
        translator = Translator() if translate else None

        for source in sources:
            source_result = {
                'source_name': source.name,
                'source_url': source.url,
                'articles': [],
                'error': None
            }

            try:
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(10)
                try:
                    feed = feedparser.parse(source.url)
                finally:
                    socket.setdefaulttimeout(old_timeout)

                if not feed.entries:
                    source_result['error'] = 'لا توجد أخبار'
                    results.append(source_result)
                    continue

                entries = feed.entries[:per_source * 2]

                def get_date(entry):
                    try:
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            return mktime(entry.published_parsed)
                        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            return mktime(entry.updated_parsed)
                        return 0
                    except Exception:
                        return 0

                entries.sort(key=get_date, reverse=True)
                entries = entries[:per_source]

                for entry in entries:
                    title = entry.get('title', '')
                    summary_raw = entry.get('summary', '') or entry.get('description', '')
                    url = entry.get('link', '')

                    if not title or not url:
                        continue

                    summary = clean_html_content(summary_raw) if summary_raw else ''

                    # Try to extract an image URL from common RSS fields
                    image_url = None
                    try:
                        # media:content
                        media_content = getattr(entry, 'media_content', None) or entry.get('media_content')
                        if media_content and isinstance(media_content, list):
                            for m in media_content:
                                if isinstance(m, dict) and m.get('url'):
                                    image_url = m['url']
                                    break

                        # media:thumbnail
                        if not image_url:
                            media_thumb = getattr(entry, 'media_thumbnail', None) or entry.get('media_thumbnail')
                            if media_thumb and isinstance(media_thumb, list):
                                for m in media_thumb:
                                    if isinstance(m, dict) and m.get('url'):
                                        image_url = m['url']
                                        break

                        # enclosure
                        if not image_url:
                            enclosures = getattr(entry, 'enclosures', None) or entry.get('enclosures')
                            if enclosures and isinstance(enclosures, list):
                                for enc in enclosures:
                                    if isinstance(enc, dict):
                                        enc_url = enc.get('url') or enc.get('href')
                                        enc_type = enc.get('type', '')
                                    else:
                                        enc_url = getattr(enc, 'href', None) or getattr(enc, 'url', None)
                                        enc_type = getattr(enc, 'type', '')
                                    if enc_url and ('image' in (enc_type or '') or enc_url.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))):
                                        image_url = enc_url
                                        break

                        # Fallback: some feeds put image URL in a generic image field
                        if not image_url:
                            image_url = entry.get('image') or entry.get('img')

                        # Final fallback: try to parse first <img src="..."> from the raw HTML summary
                        if not image_url and summary_raw:
                            try:
                                m = re.search(r'<img[^>]+src=["\\\']([^"\\\']+)["\\\']', summary_raw, re.IGNORECASE)
                                if m:
                                    image_url = m.group(1)
                            except Exception:
                                pass
                    except Exception:
                        image_url = None

                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = dt.fromtimestamp(mktime(entry.published_parsed)).isoformat()
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = dt.fromtimestamp(mktime(entry.updated_parsed)).isoformat()

                    title_ar = title
                    summary_ar = summary

                    if translate and translator:
                        try:
                            lang = 'en'
                            try:
                                from langdetect import detect
                                lang = detect(title)
                            except Exception:
                                pass

                            if lang != 'ar':
                                if title:
                                    trans = translator.translate(title, src=lang, dest='ar')
                                    title_ar = trans.text if trans else title
                                if summary:
                                    trans = translator.translate(summary[:500], src=lang, dest='ar')
                                    summary_ar = trans.text if trans else summary
                        except Exception:
                            # Keep original text if translation fails
                            pass

                    article = {
                        'id': hash(url),
                        'title_ar': title_ar,
                        'title_original': title,
                        'summary_ar': summary_ar,
                        'summary_original': summary,
                        'url': url,
                        'image_url': image_url,
                        'published_at': pub_date,
                        'sentiment': 'محايد',
                        'keyword_original': ''
                    }

                    source_result['articles'].append(article)

                results.append(source_result)

            except Exception as source_err:
                source_result['error'] = str(source_err)[:120]
                results.append(source_result)

        # Filter out completely empty sources
        results = [r for r in results if r['articles'] or r['error']]

        response_data = {
            'country': country_name,
            'sources': results,
            'total_sources': len(results),
            'total_articles': sum(len(r['articles']) for r in results)
        }

        return jsonify(response_data), 200

    except Exception:
        return jsonify({
            "error": "Internal server error",
            "code": "server_error"
        }), 500
    finally:
        db.close()


if __name__ == '__main__':
    print("\n" + "="*50)
    print("🌍 عين (Ain) - News Monitor")
    print("="*50 + "\n")

    
    # Show translation service
    print("✅ Translation: Google Translate (FREE)")
    print("ℹ️  Sentiment Analysis: Disabled (future update)")
    
    print("\n")
    # Bind to Render's PORT if available; fall back to 5555 for local dev.
    import os
    port = int(os.environ.get("PORT", 5555))
    # Disable reloader to prevent interruptions during monitoring
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=port)
