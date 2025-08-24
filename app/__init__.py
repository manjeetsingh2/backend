"""
App factory with improved logging and concise startup summary.
- Keeps your existing behavior (JWT, CORS, blueprints, security headers)
- Adds clean console logging and a readable startup block
- Includes a lightweight DB connectivity check with context + retries
"""

from __future__ import annotations

import logging
import os
import sys
import time
import platform

from flask import Flask, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from sqlalchemy import text

from app.config import get_config
from app.database import db


# -------------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------------
def _setup_pretty_logging(app: Flask) -> None:
    """
    Minimal, safe console logging setup:
    - Quiet noisy loggers (Werkzeug, SQLAlchemy engine)
    - Single concise console handler
    - Consistent, readable format
    """
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s | %(message)s", datefmt="%H:%M:%S")
    )

    if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
        app.logger.addHandler(console)

    app.logger.setLevel(logging.INFO)


# -------------------------------------------------------------------------
# Factory
# -------------------------------------------------------------------------
def create_app() -> Flask:
    app = Flask(__name__)

    # Load configuration
    config_class = get_config()
    app.config.from_object(config_class)

    # Setup logging
    _setup_pretty_logging(app)

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    jwt = JWTManager(app)

    # Configure app features
    configure_cors(app)
    configure_security_headers(app)
    configure_jwt(jwt)
    register_blueprints(app)

    # Print startup info
    _print_startup_summary(app)

    # Health check endpoint
    @app.get("/health")
    def health():
        protocol = (
            "HTTPS"
            if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https"
            else "HTTP"
        )
        return {
            "status": "ok",
            "message": f"API is running on {protocol}",
            "protocol": protocol,
            "host": request.host,
            "environment": app.config.get("ENVIRONMENT", "unknown"),
            "database": "connected" if test_db_connection() else "disconnected",
        }

    return app


# -------------------------------------------------------------------------
# CORS / Security / JWT / Blueprints
# -------------------------------------------------------------------------

def configure_cors(app: Flask) -> None:
    cors_origins = app.config.get("CORS_ORIGINS", [])

    CORS(
        app,
        origins=cors_origins,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True,
    )

    app.logger.info(f"CORS origins: {', '.join(cors_origins)}")


def configure_security_headers(app: Flask) -> None:
    @app.after_request
    def add_security_headers(response):
        is_secure = request.is_secure or request.headers.get("X-Forwarded-Proto") == "https"

        if is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        response.headers["X-Powered-By"] = "Crop-Target-API"
        response.headers["Server"] = "Flask-Production"
        return response


def configure_jwt(jwt: JWTManager) -> None:
    @jwt.additional_claims_loader
    def add_claims_to_access_token(identity):
        try:
            from app.models.user import User  # type: ignore
        except Exception:
            from models.user import User  # type: ignore

        user = User.query.get(identity)
        if user:
            role_val = getattr(user.role, "value", user.role)
            return {"role": role_val}
        return {}

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {"message": "Token has expired", "success": False}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"message": "Invalid token", "success": False}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"message": "Authorization token is required", "success": False}, 401


def register_blueprints(app: Flask) -> None:
    from auth.routes import auth_bp
    from vo.routes import vo_bp
    from bo.routes import bo_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(vo_bp)
    app.register_blueprint(bo_bp)

    app.logger.info("Blueprints registered: auth, vo, bo")


# -------------------------------------------------------------------------
# Startup Summary / DB Check
# -------------------------------------------------------------------------
def _print_startup_summary(app: Flask) -> None:
    env = app.config.get("ENVIRONMENT", "unknown")
    host = app.config.get("HOST", "127.0.0.1")
    http_port = app.config.get("HTTP_PORT", 5000)
    https_port = app.config.get("HTTPS_PORT", 5443)
    enable_http = str(app.config.get("ENABLE_HTTP", True)).lower() == "true"
    enable_https = str(app.config.get("ENABLE_HTTPS", False)).lower() == "true"

    app.logger.info("==============================================")
    app.logger.info("🌾 Crop Target API")
    app.logger.info(f"🧩 Version   : Python {platform.python_version()}")
    app.logger.info(f"🌍 Environment: {env}")
    app.logger.info(f"🐛 Debug Mode : {app.debug}")

    if enable_http:
        app.logger.info(f"🟡 HTTP  : http://{host}:{http_port}")
    if enable_https:
        app.logger.info(f"🟢 HTTPS : https://{host}:{https_port}")

    # DB check with retry
    db_ok = test_db_connection(app, retries=3, delay=1.0)
    app.logger.info(f"🩺 DB       : {'up' if db_ok else 'down'}")

    app.logger.info("✅ Startup complete")
    app.logger.info("==============================================")


def test_db_connection(app: Flask | None = None, retries: int = 1, delay: float = 0.0) -> bool:
    """
    Test database connectivity safely within app context.

    Args:
        app: Flask app instance (required at startup when context is not active)
        retries: Number of attempts to retry
        delay: Delay in seconds between retries

    Returns:
        True if connection is successful, False otherwise.
    """
    logger = logging.getLogger(__name__)
    attempt = 0

    while attempt < retries:
        try:
            if app:
                with app.app_context():
                    with db.engine.connect() as connection:
                        connection.execute(text("SELECT 1"))
            else:
                with db.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            attempt += 1
            logger.warning(f"Database connection attempt {attempt} failed: {exc}")
            if attempt < retries and delay > 0:
                time.sleep(delay)

    return False
