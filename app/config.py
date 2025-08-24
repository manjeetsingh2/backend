import os
from datetime import timedelta
from urllib.parse import quote_plus

# Force environment to development for local use
os.environ["ENVIRONMENT"] = "development"

class Config:
    ENVIRONMENT = "development"

    # === Database Configuration ===
    @staticmethod
    def get_database_uri():
        return os.getenv(
            "DATABASE_URI",
            "postgresql+psycopg://postgres:password@localhost:5432/crop_target_dev"
        )

    SQLALCHEMY_DATABASE_URI = get_database_uri.__func__()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'pool_timeout': 30,
        'connect_args': {
            'connect_timeout': 60,
            'application_name': 'crop_target_api'
        }
    }

    # === JWT ===
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    # === App Settings ===
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-app-key")
    DEBUG = True

    # === Server ===
    HOST = "127.0.0.1"
    HTTP_PORT = 5000
    HTTPS_PORT = 5443
    ENABLE_HTTP = True
    ENABLE_HTTPS = True

    # === Password Policy ===
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPER = True
    PASSWORD_REQUIRE_LOWER = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True

    # === Login Security ===
    LOGIN_RATE_LIMIT_PER_IP = 10
    LOGIN_RATE_LIMIT_WINDOW_SEC = 900
    LOGIN_RATE_LIMIT_PER_USER = 10

    # === Account Lockout ===
    ACCOUNT_LOCK_THRESHOLD = 5
    ACCOUNT_LOCK_WINDOW_SEC = 900
    ACCOUNT_LOCK_DURATION_SEC = 900

    # === Registration Rate Limit ===
    REGISTER_RATE_LIMIT_PER_IP = 20
    REGISTER_RATE_LIMIT_WINDOW_SEC = 3600

    # === CORS Configuration ===
    @staticmethod
    def get_cors_origins():
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://localhost:3000",
            "https://127.0.0.1:3000",
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "https://localhost:5443",
            "https://127.0.0.1:5443",
        ]

    CORS_ORIGINS = get_cors_origins.__func__()

    # === Security Headers ===
    SECURITY_HEADERS = {
        'development': {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
        }
    }

    @classmethod
    def get_security_headers(cls):
        return cls.SECURITY_HEADERS['development']


# === Config Mapping ===
config = {
    'development': Config,
    'default': Config
}

def get_config():
    return Config

def get_current_config():
    return Config()

def validate_config():
    try:
        config_instance = get_current_config()

        if not config_instance.SQLALCHEMY_DATABASE_URI:
            raise ValueError("Database URI not configured")

        if config_instance.JWT_SECRET_KEY == "super-secret-jwt-key":
            print("⚠️  Warning: Using default JWT secret key. OK for local, not production.")

        if config_instance.SECRET_KEY == "super-secret-app-key":
            print("⚠️  Warning: Using default app secret key. OK for local, not production.")

        if not config_instance.ENABLE_HTTP and not config_instance.ENABLE_HTTPS:
            raise ValueError("Both HTTP and HTTPS are disabled!")

        print(f"✅ Configuration validated for LOCALHOST DEVELOPMENT")
        print(f"   - Database: ✅ Configured")
        print(f"   - HTTP: {'✅ Enabled' if config_instance.ENABLE_HTTP else '❌ Disabled'}")
        print(f"   - HTTPS: {'✅ Enabled' if config_instance.ENABLE_HTTPS else '❌ Disabled'}")
        print(f"   - CORS Origins: {len(config_instance.CORS_ORIGINS)} configured")

        return True

    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def print_config_info():
    config_instance = get_current_config()
    print("\n" + "=" * 60)
    print("🔧 LOCALHOST DEVELOPMENT CONFIGURATION")
    print("=" * 60)
    print(f"Environment: {config_instance.ENVIRONMENT}")
    print(f"Debug Mode: {config_instance.DEBUG}")
    print(f"Host: {config_instance.HOST}")
    print(f"HTTP Port: {config_instance.HTTP_PORT} ({'✅ Enabled' if config_instance.ENABLE_HTTP else '❌ Disabled'})")
    print(f"HTTPS Port: {config_instance.HTTPS_PORT} ({'✅ Enabled' if config_instance.ENABLE_HTTPS else '❌ Disabled'})")
    print(f"Database: {config_instance.SQLALCHEMY_DATABASE_URI[:50]}...")
    print(f"CORS Origins ({len(config_instance.CORS_ORIGINS)}):")
    for i, origin in enumerate(config_instance.CORS_ORIGINS, 1):
        print(f"  {i}. {origin}")
    print("=" * 60)


if __name__ == "__main__":
    print_config_info()
    validate_config()
