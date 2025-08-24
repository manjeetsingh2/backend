import re
from flask import current_app

SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{};':\",.<>/?`~\\|"

def validate_password_strength(password: str):
    """Validate password against security policy"""
    conf = current_app.config
    errors = []
    
    if len(password) < conf['PASSWORD_MIN_LENGTH']:
        errors.append(f"Password must be at least {conf['PASSWORD_MIN_LENGTH']} characters long")
    
    if conf['PASSWORD_REQUIRE_UPPER'] and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if conf['PASSWORD_REQUIRE_LOWER'] and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if conf['PASSWORD_REQUIRE_DIGIT'] and not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if conf['PASSWORD_REQUIRE_SPECIAL'] and not re.search(rf'[{re.escape(SPECIAL_CHARS)}]', password):
        errors.append("Password must contain at least one special character (!@#$%^&* etc.)")
    
    return errors
