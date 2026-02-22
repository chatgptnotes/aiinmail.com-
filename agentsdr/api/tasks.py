"""Tasks API."""
from flask import request, jsonify, current_app
from agentsdr.api import api_bp
from agentsdr.api.auth import api_login_required
from agentsdr.core.supabase_client import get_service_supabase
import uuid


@api_bp.route('/tasks', methods=['GET'])
@api_login_required
def list_tasks():
    limit = request.args.get('limit', 50, type=int)
    status = request.args.get('status')
    try:
        sb = get_service_supabase()
        q = sb.table('agent_tasks').select('*').order('created_at', desc=True).limit(limit)
        if status and status != 'all':
            q = q.eq('status', status)
        result = q.execute()
        return jsonify({'tasks': result.data or []})
    except Exception as e:
        current_app.logger.error(f"List tasks error: {e}")
        return jsonify({'tasks': []})


@api_bp.route('/tasks', methods=['POST'])
@api_login_required
def create_task():
    data = request.get_json() or {}
    title = data.get('title')
    if not title:
        return jsonify({'error': 'Title required'}), 400
    try:
        sb = get_service_supabase()
        task = {
            'id': str(uuid.uuid4()),
            'title': title,
            'description': data.get('description', ''),
            'status': data.get('status', 'pending'),
            'priority': data.get('priority', 'medium'),
            'agent_id': data.get('agent_id'),
        }
        sb.table('agent_tasks').insert(task).execute()
        return jsonify(task), 201
    except Exception as e:
        current_app.logger.error(f"Create task error: {e}")
        return jsonify({'error': 'Failed to create task'}), 500
