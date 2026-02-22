"""API Authentication endpoints using JWT via Supabase tokens."""
from flask import request, jsonify, current_app
from functools import wraps
from agentsdr.api import api_bp
from agentsdr.core.supabase_client import get_supabase, get_service_supabase
from agentsdr.auth.models import User


def get_current_api_user():
    """Extract user from Authorization: Bearer <supabase_access_token>."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:]
    try:
        sb = get_service_supabase()
        # Verify token via Supabase auth
        res = sb.auth.get_user(token)
        if res and res.user:
            user = User.get_by_email(res.user.email)
            if not user:
                user = User.create_user(
                    email=res.user.email,
                    display_name=res.user.user_metadata.get('full_name', res.user.email.split('@')[0])
                )
            return user
    except Exception as e:
        current_app.logger.debug(f"API auth failed: {e}")
    return None


def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_api_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        request._api_user = user
        return f(*args, **kwargs)
    return decorated


@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    """Login with email/password, returns Supabase session tokens."""
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    try:
        sb = get_supabase()
        res = sb.auth.sign_in_with_password({'email': email, 'password': password})
        if res.user:
            user = User.get_by_email(email)
            if not user:
                user = User.create_user(email=email, display_name=email.split('@')[0])
            return jsonify({
                'access_token': res.session.access_token,
                'refresh_token': res.session.refresh_token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'display_name': user.display_name,
                    'is_super_admin': user.is_super_admin,
                }
            })
    except Exception as e:
        current_app.logger.error(f"API login error: {e}")
    return jsonify({'error': 'Invalid credentials'}), 401


@api_bp.route('/auth/register', methods=['POST'])
def api_register():
    """Register new user."""
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', '')
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    try:
        sb = get_supabase()
        res = sb.auth.sign_up({
            'email': email,
            'password': password,
            'options': {'data': {'full_name': name}}
        })
        if res.user:
            user = User.create_user(email=email, display_name=name or email.split('@')[0])
            return jsonify({
                'access_token': res.session.access_token if res.session else None,
                'refresh_token': res.session.refresh_token if res.session else None,
                'user': {
                    'id': user.id if user else res.user.id,
                    'email': email,
                    'display_name': name,
                }
            }), 201
    except Exception as e:
        current_app.logger.error(f"API register error: {e}")
        return jsonify({'error': str(e)}), 400
    return jsonify({'error': 'Registration failed'}), 400


@api_bp.route('/auth/me', methods=['GET'])
@api_login_required
def api_me():
    """Get current user info."""
    user = request._api_user
    orgs = user.get_organizations()
    return jsonify({
        'id': user.id,
        'email': user.email,
        'display_name': user.display_name,
        'is_super_admin': user.is_super_admin,
        'organizations': orgs,
    })


@api_bp.route('/auth/logout', methods=['POST'])
def api_logout():
    """Logout (client should discard tokens)."""
    return jsonify({'message': 'Logged out'})
