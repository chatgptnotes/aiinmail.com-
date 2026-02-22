"""Digital Agents API — 6 C-Suite AI agents."""
from flask import request, jsonify, current_app
from agentsdr.api import api_bp
from agentsdr.api.auth import api_login_required
from agentsdr.core.supabase_client import get_service_supabase
from datetime import datetime

AGENT_DEFINITIONS = {
    'cmo': {
        'role': 'cmo',
        'name': 'Digital CMO',
        'title': 'Chief Marketing Officer',
        'description': 'AI-powered marketing strategist. Manages outreach campaigns, tracks email opens, and optimizes marketing funnels.',
        'capabilities': ['email_outreach', 'campaign_management', 'open_tracking', 'ab_testing', 'lead_scoring', 'content_strategy'],
        'color': '#3B82F6',
    },
    'cro': {
        'role': 'cro',
        'name': 'Digital CRO',
        'title': 'Chief Revenue Officer',
        'description': 'Revenue optimization engine. Tracks deals via HubSpot, monitors conversion rates, and automates follow-ups.',
        'capabilities': ['deal_tracking', 'conversion_optimization', 'pipeline_management', 'revenue_forecasting', 'follow_up_automation', 'quota_tracking'],
        'color': '#10B981',
    },
    'cfo': {
        'role': 'cfo',
        'name': 'Digital CFO',
        'title': 'Chief Financial Officer',
        'description': 'Financial intelligence agent. Handles invoice tracking, payment reminders, and financial summaries.',
        'capabilities': ['invoice_tracking', 'payment_reminders', 'financial_reporting', 'budget_analysis', 'expense_categorization', 'cash_flow_forecast'],
        'color': '#8B5CF6',
    },
    'coo': {
        'role': 'coo',
        'name': 'Digital COO',
        'title': 'Chief Operations Officer',
        'description': 'Operations commander. Schedules tasks, coordinates teams, and ensures SOP compliance.',
        'capabilities': ['task_scheduling', 'team_coordination', 'sop_compliance', 'workflow_automation', 'resource_allocation', 'performance_tracking'],
        'color': '#F59E0B',
    },
    'cto': {
        'role': 'cto',
        'name': 'Digital CTO',
        'title': 'Chief Technology Officer',
        'description': 'Tech operations guardian. Monitors system health, deployment status, and manages technical infrastructure.',
        'capabilities': ['system_monitoring', 'deployment_management', 'code_review', 'security_audit', 'infrastructure_scaling', 'tech_debt_tracking'],
        'color': '#6366F1',
    },
    'cxo': {
        'role': 'cxo',
        'name': 'Digital CXO',
        'title': 'Chief Experience Officer',
        'description': 'Customer experience analyst. Tracks NPS, analyzes feedback, and manages support tickets.',
        'capabilities': ['feedback_analysis', 'nps_tracking', 'support_tickets', 'sentiment_analysis', 'customer_journey_mapping', 'churn_prediction'],
        'color': '#EC4899',
    },
}


def _get_agent_status(role: str) -> dict:
    """Get agent with live status from DB, falling back to definition defaults."""
    defn = AGENT_DEFINITIONS.get(role)
    if not defn:
        return None
    agent = {**defn, 'status': 'idle', 'last_run': None, 'tasks_completed': 0}
    try:
        sb = get_service_supabase()
        rows = sb.table('agents').select('*').eq('type', role).execute()
        if rows.data:
            row = rows.data[0]
            agent['status'] = row.get('status', 'idle')
            agent['tasks_completed'] = (row.get('metrics') or {}).get('tasks_completed', 0)
            agent['last_run'] = row.get('updated_at')
            agent['metrics'] = row.get('metrics', {})
            agent['id'] = row.get('id')
    except Exception as e:
        current_app.logger.debug(f"Agent DB lookup failed for {role}: {e}")
    return agent


@api_bp.route('/agents', methods=['GET'])
@api_login_required
def list_agents():
    agents = [_get_agent_status(r) for r in AGENT_DEFINITIONS]
    return jsonify(agents)


@api_bp.route('/agents/<role>', methods=['GET'])
@api_login_required
def get_agent(role):
    agent = _get_agent_status(role)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    # Include recent tasks
    try:
        sb = get_service_supabase()
        tasks = sb.table('agent_tasks').select('*').eq('agent_id', agent.get('id', '')).order('created_at', desc=True).limit(10).execute()
        agent['recent_tasks'] = tasks.data or []
    except Exception:
        agent['recent_tasks'] = []
    return jsonify(agent)


@api_bp.route('/agents/<role>/run', methods=['POST'])
@api_login_required
def run_agent(role):
    """Trigger an agent task."""
    if role not in AGENT_DEFINITIONS:
        return jsonify({'error': 'Agent not found'}), 404
    data = request.get_json() or {}
    task_type = data.get('task', 'default')
    try:
        sb = get_service_supabase()
        # Find or create agent record
        rows = sb.table('agents').select('id').eq('type', role).execute()
        agent_id = rows.data[0]['id'] if rows.data else None
        if not agent_id:
            import uuid
            agent_id = str(uuid.uuid4())
            sb.table('agents').insert({
                'id': agent_id,
                'name': AGENT_DEFINITIONS[role]['name'],
                'type': role,
                'status': 'active',
                'config': {},
                'metrics': {'tasks_completed': 0},
            }).execute()

        # Create task
        import uuid
        task_id = str(uuid.uuid4())
        sb.table('agent_tasks').insert({
            'id': task_id,
            'agent_id': agent_id,
            'title': f"{AGENT_DEFINITIONS[role]['name']} — {task_type}",
            'description': data.get('description', f'Running {task_type} task'),
            'status': 'pending',
            'priority': data.get('priority', 'medium'),
        }).execute()

        # Update agent status
        sb.table('agents').update({'status': 'working', 'updated_at': datetime.utcnow().isoformat()}).eq('id', agent_id).execute()

        return jsonify({'task_id': task_id, 'status': 'pending', 'message': f'{AGENT_DEFINITIONS[role]["name"]} task queued'})
    except Exception as e:
        current_app.logger.error(f"Run agent error: {e}")
        return jsonify({'error': 'Failed to run agent'}), 500
