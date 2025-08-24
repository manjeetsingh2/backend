from flask import Blueprint, request, current_app
from marshmallow import ValidationError
from app.utils import safe_execute, success_response, error_response
from auth.services import AuthService
from app.database import db

# 🔐 Security imports
from app.security import validate_password_strength
from app.ratelimit import allow_login_ip, allow_login_user, allow_register_ip

# 📝 Schema imports (NEW - EXTERNAL SCHEMAS)
from auth.schemas import RegisterSchema, LoginSchema

# Blueprint and service
auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')
auth_service = AuthService()

# ❌ REMOVED: Inline schema definitions (now imported from auth.schemas)

# 🔄 Updated /register route
@auth_bp.route('/register', methods=['POST'])
@safe_execute
def register():
    try:
        # ✅ Use external schema
        schema = RegisterSchema()
        data = schema.load(request.get_json() or {})
        
        # 🚫 Rate limit registration by IP
        if not allow_register_ip():
            return error_response("Too many registration attempts. Try again later.", 429)
        
        # 🔐 Password strength validation (server-side)
        password_errors = validate_password_strength(data['password'])
        if password_errors:
            return error_response("Password does not meet security requirements", 400, {
                "password_errors": password_errors
            })
        
        # 👤 Create user
        result = auth_service.register_user(
            data['username'], 
            data['password'], 
            data['role']
        )
        
        return success_response(result, "User registered successfully", 201)
        
    except ValidationError as e:
        return error_response("Invalid input data", 400, e.messages)


# 🔄 Updated /login route
@auth_bp.route('/login', methods=['POST'])
@safe_execute
def login():
    try:
        # ✅ Use external schema
        schema = LoginSchema()
        data = schema.load(request.get_json() or {})
        
        username = data['username'].strip()
        
        # 🚫 Rate limit login by IP
        if not allow_login_ip():
            return error_response("Too many login attempts from this IP. Try again later.", 429)
        
        # 🚫 Rate limit login by username
        if username and not allow_login_user(username):
            return error_response("Too many login attempts for this user. Try again later.", 429)
        
        # 🔍 Find user
        from models.user import User
        user = User.query.filter_by(username=username).first()
        
        if not user:
            # Vague error to prevent user enumeration
            return error_response("Invalid username or password", 401)
        
        # 🔒 Check if account is locked
        if user.is_locked():
            return error_response(
                "Account is temporarily locked due to multiple failed login attempts. Try again later.",
                423
            )
        
        # 🔐 Verify password
        if not user.check_password(data['password']):
            # Register failed attempt and potentially lock account
            user.register_failed_login(current_app.config)
            db.session.commit()
            return error_response("Invalid username or password", 401)
        
        # ✅ Successful login - reset failed login counters
        user.reset_failed_logins()
        db.session.commit()
        
        # 🎫 Create JWT token
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role}
        )
        
        return success_response({
            "access_token": access_token,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role
            }
        }, "Login successful")
        
    except ValidationError as e:
        return error_response("Invalid input data", 400, e.messages)


# 🔍 Optional: Health check for auth module
@auth_bp.route('/health', methods=['GET'])
def auth_health():
    """Health check for authentication module"""
    return success_response({
        "module": "auth",
        "status": "healthy",
        "endpoints": [
            "POST /api/v1/auth/register",
            "POST /api/v1/auth/login"
        ]
    }, "Auth module is healthy")


# 🔧 Optional: Get current user info (requires JWT)
@auth_bp.route('/me', methods=['GET'])
@safe_execute
def get_current_user():
    """Get current authenticated user information"""
    try:
        from flask_jwt_extended import jwt_required, get_jwt_identity
        from models.user import User
        
        @jwt_required()
        def _get_user():
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            
            if not user:
                return error_response("User not found", 404)
            
            return success_response({
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "role": user.role,
                    "created_at": user.created_at.isoformat(),
                    "is_locked": user.is_locked(),
                    "failed_login_count": user.failed_login_count
                }
            }, "User information retrieved")
        
        return _get_user()
        
    except Exception as e:
        return error_response(f"Error retrieving user info: {str(e)}", 500)
