from app.routes.auth import auth_bp
from app.routes.main import main_bp
from app.routes.reports import reports_bp
from app.routes.claims import claims_bp
from app.routes.messages import messages_bp
from app.routes.handovers import handovers_bp
from app.routes.user import user_bp
from app.routes.notifications import notifications_bp
from app.routes.admin import admin_bp
from app.routes.analytics import analytics_bp
from app.routes.api import api_bp

__all__ = [
    'auth_bp',
    'main_bp',
    'reports_bp',
    'claims_bp',
    'messages_bp',
    'handovers_bp',
    'user_bp',
    'notifications_bp',
    'admin_bp',
    'analytics_bp',
    'api_bp'
]

