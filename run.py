import os
from app import create_app
from app.extensions import socketio, db
from app.models import (
    User, Department, CampusLocation, ItemCategory,
    LostReport, FoundReport, Claim, Handover, ItemMatch
)

config_name = os.environ.get('FLASK_CONFIG', 'development')
app = create_app(config_name)

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Department': Department,
        'CampusLocation': CampusLocation,
        'ItemCategory': ItemCategory,
        'LostReport': LostReport,
        'FoundReport': FoundReport,
        'Claim': Claim,
        'Handover': Handover,
        'ItemMatch': ItemMatch
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() in ['true', '1']
    print(f"Starting CampusConnect Web Application on http://127.0.0.1:{port}")
    socketio.run(app, host='127.0.0.1', port=port, debug=debug, allow_unsafe_werkzeug=True)

