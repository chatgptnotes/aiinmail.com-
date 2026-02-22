from flask import Blueprint

api_bp = Blueprint('api', __name__)

from agentsdr.api import auth, agents, orgs, emails, crm, tasks, analytics  # noqa
