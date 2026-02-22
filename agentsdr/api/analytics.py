"""Analytics API — dashboard stats."""
from flask import jsonify, current_app
from agentsdr.api import api_bp
from agentsdr.api.auth import api_login_required
from agentsdr.core.supabase_client import get_service_supabase


@api_bp.route('/analytics', methods=['GET'])
@api_login_required
def get_analytics():
    stats = {
        'agents': {'total': 6, 'active': 0, 'idle': 0},
        'tasks': {'total': 0, 'completed': 0, 'pending': 0, 'in_progress': 0},
        'emails': {'total': 0, 'unread': 0},
        'deals': {'total': 0, 'won': 0, 'pipeline_value': 0},
        'activity': [],
    }
    try:
        sb = get_service_supabase()

        # Agent stats
        try:
            agents = sb.table('agents').select('status').execute()
            for a in (agents.data or []):
                s = a.get('status', 'idle')
                if s in ('active', 'working'):
                    stats['agents']['active'] += 1
                else:
                    stats['agents']['idle'] += 1
        except Exception:
            pass

        # Task stats
        try:
            tasks = sb.table('agent_tasks').select('status').execute()
            for t in (tasks.data or []):
                stats['tasks']['total'] += 1
                s = t.get('status', 'pending')
                if s == 'completed':
                    stats['tasks']['completed'] += 1
                elif s == 'in-progress':
                    stats['tasks']['in_progress'] += 1
                else:
                    stats['tasks']['pending'] += 1
        except Exception:
            pass

        # Email stats
        try:
            emails = sb.table('emails').select('id', count='exact').execute()
            stats['emails']['total'] = emails.count or len(emails.data or [])
        except Exception:
            pass

        # Recent activity
        try:
            activity = sb.table('activity_log').select('*').order('created_at', desc=True).limit(10).execute()
            stats['activity'] = activity.data or []
        except Exception:
            pass

    except Exception as e:
        current_app.logger.error(f"Analytics error: {e}")

    return jsonify(stats)
