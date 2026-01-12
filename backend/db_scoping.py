"""
Database Scoping Helpers for User Isolation

This module provides consistent, reusable functions for enforcing
user-level data isolation across all endpoints.

Usage:
    from db_scoping import scope_to_user, get_user_record_or_404

IMPORTANT: All user-owned data MUST be filtered through these helpers
to prevent data leakage between users.
"""
from flask import abort
from flask_login import current_user


# Tables that require user_id filtering (user-owned data)
USER_OWNED_TABLES = {
    'keywords',      # Keyword
    'articles',      # Article
    'exports',       # ExportRecord
    'user_files',    # UserFile
    'search_history', # SearchHistory
    'user_articles', # UserArticle (junction - not actively used)
    'user_countries', # UserCountry (junction - not actively used)
    'user_sources',  # UserSource (junction - not actively used)
}

# Tables that are shared catalog (no user filtering needed)
SHARED_CATALOG_TABLES = {
    'countries',     # Country (shared catalog)
    'sources',       # Source (shared catalog)
}

# System tables (admin only or special handling)
SYSTEM_TABLES = {
    'users',         # User management (admin only)
    'audit_log',     # AuditLog (system/admin)
}


def scope_to_user(query, Model, user_id=None, force=True):
    """
    Filter a query to only return records owned by the specified user.
    
    Args:
        query: SQLAlchemy query object
        Model: The model class being queried
        user_id: User ID to filter by. If None, uses current_user.id
        force: If True, always apply filter even for admins (recommended for user data)
    
    Returns:
        Filtered query
    
    Raises:
        ValueError: If Model doesn't have user_id column but filtering is required
    
    Example:
        # In an endpoint:
        from db_scoping import scope_to_user
        
        articles = scope_to_user(db.query(Article), Article).all()
    """
    # Determine user_id
    if user_id is None:
        if not current_user.is_authenticated:
            raise ValueError("User must be authenticated for user-scoped queries")
        user_id = current_user.id
    
    # Check if model has user_id column
    if not hasattr(Model, 'user_id'):
        # Model doesn't have user_id - likely a shared catalog table
        return query
    
    # Always filter by user_id for user-owned data
    return query.filter(Model.user_id == user_id)


def get_user_record_or_404(db, Model, record_id, user_id=None):
    """
    Get a single record by ID, ensuring it belongs to the specified user.
    Returns 404 if not found or doesn't belong to user.
    
    Args:
        db: Database session
        Model: The model class
        record_id: Primary key ID of the record
        user_id: User ID to verify ownership. If None, uses current_user.id
    
    Returns:
        The record if found and owned by user
    
    Raises:
        404 abort if record not found or not owned by user
    
    Example:
        # In an endpoint:
        from db_scoping import get_user_record_or_404
        
        keyword = get_user_record_or_404(db, Keyword, keyword_id)
    """
    if user_id is None:
        if not current_user.is_authenticated:
            abort(401, description="Authentication required")
        user_id = current_user.id
    
    # Check if model has user_id column
    if hasattr(Model, 'user_id'):
        record = db.query(Model).filter(
            Model.id == record_id,
            Model.user_id == user_id
        ).first()
    else:
        # Model doesn't have user_id - just get by ID
        record = db.query(Model).filter(Model.id == record_id).first()
    
    if record is None:
        abort(404, description=f"{Model.__name__} not found")
    
    return record


def ensure_user_owns(record, user_id=None):
    """
    Verify that a record is owned by the specified user.
    
    Args:
        record: The database record to check
        user_id: User ID to verify. If None, uses current_user.id
    
    Raises:
        403 abort if record doesn't belong to user
        ValueError if record doesn't have user_id attribute
    
    Example:
        # After fetching a record:
        ensure_user_owns(keyword)
    """
    if user_id is None:
        if not current_user.is_authenticated:
            abort(401, description="Authentication required")
        user_id = current_user.id
    
    if not hasattr(record, 'user_id'):
        raise ValueError(f"{type(record).__name__} doesn't have user_id attribute")
    
    if record.user_id != user_id:
        abort(403, description="Access denied - you don't own this resource")


def require_auth():
    """
    Decorator-style check to ensure user is authenticated.
    Call at the start of any endpoint that requires authentication.
    
    Example:
        @app.route('/api/something')
        def something():
            require_auth()
            # ... rest of code
    """
    if not current_user.is_authenticated:
        abort(401, description="Authentication required")


def require_admin():
    """
    Check that current user is an admin.
    
    Example:
        @app.route('/api/admin/something')
        def admin_something():
            require_admin()
            # ... rest of code
    """
    require_auth()
    if getattr(current_user, 'role', 'USER') != 'ADMIN':
        abort(403, description="Admin access required")


# Alias for backward compatibility with existing scoped() function
def scoped(query, Model, force_user_filter=True):
    """
    Backward-compatible wrapper around scope_to_user.
    
    DEPRECATED: Use scope_to_user() directly for new code.
    
    Args:
        query: SQLAlchemy query
        Model: Model class
        force_user_filter: If True, always filter by user_id (recommended)
    
    Returns:
        Filtered query
    """
    if not current_user.is_authenticated:
        return query
    
    if force_user_filter:
        return scope_to_user(query, Model, current_user.id, force=True)
    
    # Legacy behavior: admins see all (NOT recommended for user data)
    if getattr(current_user, 'role', 'USER') == 'ADMIN':
        return query
    
    return scope_to_user(query, Model, current_user.id, force=True)
