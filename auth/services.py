from app.database import db
from models.user import User
from flask_jwt_extended import create_access_token

class AuthService:
    
    def register_user(self, username, password, role):
        # Check if user exists
        if User.query.filter_by(username=username).first():
            raise ValueError("Username already exists")
        
        # Validate role
        if role not in ['VO', 'BO']:
            raise ValueError("Invalid role. Must be VO or BO")
        
        # Create user
        user = User(username=username, role=role)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return {"id": str(user.id), "username": user.username, "role": user.role}
    
    def login_user(self, username, password):
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            raise ValueError("Invalid username or password")
        
        # Create JWT token
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role}
        )
        
        return {
            "access_token": access_token,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role
            }
        }
