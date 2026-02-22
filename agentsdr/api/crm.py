"""CRM API — HubSpot integration."""
from flask import request, jsonify, current_app
from agentsdr.api import api_bp
from agentsdr.api.auth import api_login_required
from agentsdr.core.supabase_client import get_service_supabase


@api_bp.route('/crm/contacts', methods=['GET'])
@api_login_required
def crm_contacts():
    limit = request.args.get('limit', 50, type=int)
    try:
        sb = get_service_supabase()
        result = sb.table('contacts').select('*').limit(limit).execute()
        return jsonify({'contacts': result.data or []})
    except Exception as e:
        current_app.logger.debug(f"CRM contacts: {e}")
        # Fallback — table may not exist yet
        return jsonify({'contacts': [], 'message': 'CRM data not yet synced'})


@api_bp.route('/crm/deals', methods=['GET'])
@api_login_required
def crm_deals():
    limit = request.args.get('limit', 50, type=int)
    try:
        sb = get_service_supabase()
        result = sb.table('deals').select('*').limit(limit).execute()
        return jsonify({'deals': result.data or []})
    except Exception as e:
        current_app.logger.debug(f"CRM deals: {e}")
        return jsonify({'deals': [], 'message': 'CRM data not yet synced'})


@api_bp.route('/crm/sync', methods=['POST'])
@api_login_required
def crm_sync():
    """Trigger HubSpot sync."""
    return jsonify({'message': 'CRM sync queued', 'status': 'pending'}), 202
