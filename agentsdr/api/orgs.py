"""Organizations API."""
from flask import request, jsonify, current_app
from agentsdr.api import api_bp
from agentsdr.api.auth import api_login_required
from agentsdr.core.supabase_client import get_service_supabase
from datetime import datetime
import uuid


@api_bp.route('/orgs', methods=['GET'])
@api_login_required
def list_orgs():
    user = request._api_user
    try:
        sb = get_service_supabase()
        memberships = sb.table('organization_members').select('org_id, role').eq('user_id', user.id).execute()
        org_ids = [m['org_id'] for m in (memberships.data or [])]
        if not org_ids:
            return jsonify([])
        orgs = sb.table('organizations').select('*').in_('id', org_ids).execute()
        # Attach user role
        role_map = {m['org_id']: m['role'] for m in memberships.data}
        result = []
        for o in (orgs.data or []):
            o['user_role'] = role_map.get(o['id'], 'member')
            result.append(o)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"List orgs error: {e}")
        return jsonify([])


@api_bp.route('/orgs', methods=['POST'])
@api_login_required
def create_org():
    user = request._api_user
    data = request.get_json() or {}
    name = data.get('name')
    slug = data.get('slug', '').lower().replace(' ', '-')
    if not name:
        return jsonify({'error': 'Name required'}), 400
    if not slug:
        slug = name.lower().replace(' ', '-')
    try:
        sb = get_service_supabase()
        existing = sb.table('organizations').select('id').eq('slug', slug).execute()
        if existing.data:
            return jsonify({'error': 'Slug already exists'}), 400
        org_id = str(uuid.uuid4())
        sb.table('organizations').insert({
            'id': org_id, 'name': name, 'slug': slug,
            'owner_user_id': user.id,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        }).execute()
        sb.table('organization_members').insert({
            'id': str(uuid.uuid4()), 'org_id': org_id,
            'user_id': user.id, 'role': 'admin',
            'joined_at': datetime.utcnow().isoformat(),
        }).execute()
        return jsonify({'id': org_id, 'name': name, 'slug': slug}), 201
    except Exception as e:
        current_app.logger.error(f"Create org error: {e}")
        return jsonify({'error': 'Failed to create organization'}), 500


@api_bp.route('/orgs/<org_id>', methods=['GET'])
@api_login_required
def get_org(org_id):
    try:
        sb = get_service_supabase()
        org = sb.table('organizations').select('*').eq('id', org_id).execute()
        if not org.data:
            return jsonify({'error': 'Not found'}), 404
        members = sb.table('organization_members').select('user_id, role, joined_at').eq('org_id', org_id).execute()
        result = org.data[0]
        result['members'] = members.data or []
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Get org error: {e}")
        return jsonify({'error': 'Failed to fetch organization'}), 500
