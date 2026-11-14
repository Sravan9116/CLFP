import os
from flask import Flask, render_template
from flask_socketio import join_room, leave_room
from flask_login import current_user
from config import config
from app.extensions import db, migrate, login_manager, mail, csrf, socketio
from app.models.notification import Notification, Announcement

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Ensure upload directories exist
    upload_folder = app.config['UPLOAD_FOLDER']
    os.makedirs(os.path.join(upload_folder, 'reports'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'evidence'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'qrcodes'), exist_ok=True)
    
    # Context processors
    @app.context_processor
    def inject_global_data():
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        announcement_count = Announcement.query.filter_by(status='active').count()
        return {
            'unread_notifications_count': unread_count,
            'active_announcements_count': announcement_count,
            'current_year': 2026,
            'campus_name': 'CampusConnect University'
        }
        
    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # Register blueprints
    from app.routes import (
        auth_bp, main_bp, reports_bp, claims_bp,
        messages_bp, handovers_bp, user_bp,
        notifications_bp, admin_bp, analytics_bp, api_bp
    )
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(claims_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(handovers_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(api_bp)
    
    # Register SocketIO event handlers
    register_socketio_events(socketio)
    
    return app

def register_socketio_events(socketio_instance):
    @socketio_instance.on('connect')
    def handle_connect():
        if current_user.is_authenticated:
            # Join personal notification room
            personal_room = f"user_{current_user.id}"
            join_room(personal_room)
            
            # If admin, also join admin alerts room
            if current_user.is_admin:
                join_room('admin_room')
                
            socketio_instance.emit('connection_response', {
                'status': 'connected',
                'user_id': current_user.id,
                'role': current_user.role
            })

    @socketio_instance.on('join_claim')
    def handle_join_claim(data):
        claim_id = data.get('claim_id')
        if claim_id and current_user.is_authenticated:
            # Check permission: claimant or admin
            from app.models.claim import Claim
            claim = Claim.query.get(claim_id)
            if claim and (claim.claimant_id == current_user.id or current_user.is_admin):
                room_name = f"claim_{claim_id}"
                join_room(room_name)
                socketio_instance.emit('room_joined', {'room': room_name})

    @socketio_instance.on('leave_claim')
    def handle_leave_claim(data):
        claim_id = data.get('claim_id')
        if claim_id:
            leave_room(f"claim_{claim_id}")

