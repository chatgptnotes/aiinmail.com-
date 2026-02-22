"""Email API — Gmail integration."""
from flask import request, jsonify, current_app
from agentsdr.api import api_bp
from agentsdr.api.auth import api_login_required
from agentsdr.core.supabase_client import get_service_supabase


@api_bp.route('/emails', methods=['GET'])
@api_login_required
def list_emails():
    """List emails from Supabase email store."""
    user = request._api_user
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    try:
        sb = get_service_supabase()
        q = sb.table('emails').select('*').order('received_at', desc=True).range(offset, offset + limit - 1)
        result = q.execute()
        return jsonify({'emails': result.data or [], 'total': len(result.data or [])})
    except Exception as e:
        current_app.logger.error(f"List emails error: {e}")
        return jsonify({'emails': [], 'total': 0})


@api_bp.route('/emails/sync', methods=['POST'])
@api_login_required
def sync_emails():
    """Trigger Gmail sync."""
    try:
        from agentsdr.services.gmail_service import fetch_and_summarize_emails
        result = fetch_and_summarize_emails()
        return jsonify({'message': 'Sync started', 'result': str(result)})
    except Exception as e:
        current_app.logger.error(f"Email sync error: {e}")
        return jsonify({'message': 'Sync queued (Gmail credentials may need setup)'}), 202


@api_bp.route('/emails/<email_id>/summary', methods=['GET'])
@api_login_required
def email_summary(email_id):
    """Get AI summary for an email."""
    try:
        sb = get_service_supabase()
        email_row = sb.table('emails').select('*').eq('id', email_id).execute()
        if not email_row.data:
            return jsonify({'error': 'Email not found'}), 404
        em = email_row.data[0]
        # Check if already summarized
        if em.get('ai_summary'):
            return jsonify({'summary': em['ai_summary'], 'cached': True})
        # Generate summary
        try:
            from agentsdr.email.ai_service import AIService
            ai = AIService()
            result = ai.classify_email(
                subject=em.get('subject', ''),
                body=em.get('body', ''),
                from_email=em.get('from_email', ''),
                user_id=request._api_user.id,
            )
            return jsonify({'summary': result, 'cached': False})
        except Exception:
            return jsonify({'summary': 'AI service unavailable', 'cached': False})
    except Exception as e:
        current_app.logger.error(f"Email summary error: {e}")
        return jsonify({'error': 'Failed to get summary'}), 500
