#!/usr/bin/env python3
"""
Cachenet CDN Platform Authentication Routes
JWT-based authentication with user management
"""

import os
import secrets
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            logger.warning(f"Failed login attempt for email: {email}")
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is disabled'}), 401
        
        # Create access token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(hours=24)
        )
        
        # Update last login
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Successful login for user: {user.email}")
        
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict(),
            'expires_in': 86400  # 24 hours in seconds
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register new user account"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'username', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data or not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        email = data['email'].lower().strip()
        username = data['username'].lower().strip()
        password = data['password']
        
        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already taken'}), 409
        
        # Create new user
        user = User(
            email=email,
            username=username,
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            company=data.get('company', '').strip(),
            phone=data.get('phone', '').strip(),
            api_key=secrets.token_urlsafe(32)
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"New user registered: {user.email}")
        
        # Create access token for immediate login
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(hours=24)
        )
        
        return jsonify({
            'message': 'Registration successful',
            'access_token': access_token,
            'user': user.to_dict(),
            'expires_in': 86400
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'company', 'phone']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field].strip() if data[field] else '')
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Profile updated for user: {user.email}")
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data or not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Current and new passwords required'}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400
        
        # Update password
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Password changed for user: {user.email}")
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/api-key', methods=['POST'])
@jwt_required()
def regenerate_api_key():
    """Regenerate user API key"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Generate new API key
        user.api_key = secrets.token_urlsafe(32)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"API key regenerated for user: {user.email}")
        
        return jsonify({
            'message': 'API key regenerated successfully',
            'api_key': user.api_key
        }), 200
        
    except Exception as e:
        logger.error(f"Regenerate API key error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    """List all users (admin only)"""
    try:
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        users = User.query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@jwt_required()
def toggle_user_status():
    """Toggle user active status (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        if target_user.id == current_user.id:
            return jsonify({'error': 'Cannot disable your own account'}), 400
        
        target_user.is_active = not target_user.is_active
        target_user.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = 'enabled' if target_user.is_active else 'disabled'
        logger.info(f"User {target_user.email} {status} by admin {current_user.email}")
        
        return jsonify({
            'message': f'User {status} successfully',
            'user': target_user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Toggle user status error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500