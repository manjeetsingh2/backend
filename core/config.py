"""
Application configuration management (env-driven)
Keeps CORS, ports, security, and DB in sync with server.py
"""

import os
from functools import lru_cache
from typing import List

# Optionally load .env if not already loaded elsewhere
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


class Settings:
    """Application settings with environment-based configuration"""

    def __init__(self):
        # Environment
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.debug: bool = os.getenv("DEBUG", "true").lower() == "true"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

        # Protocol / Ports
        self.use_https: bool = os.getenv("USE_HTTPS", "false").lower() == "true"
        self.http_port: int = int(os.getenv("HTTP_PORT", "8001"))
        self.https_port: int = int(os.getenv("HTTPS_PORT", "8443"))


        # # API host/port (optional, for reverse proxies or separate runners)
        # self.api_host: str = os.getenv("API_HOST", "0.0.0.0")
        # self.api_port: int = int(os.getenv("API_PORT", str(self.http_port)))

        # Database
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql://agri_user:agri_secure_pass_2024@localhost:5432/agri_development",
        )

        # Security / JWT
        self.jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "agri-jwt-secret-key-2024")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        # Support both minutes and hours styles; prefer minutes if provided
        self.jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
        self.jwt_expiration_hours: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

        # CORS (protocol-aware). Do NOT use a generic CORS_ORIGINS anymore.
        self.cors_origins_http: List[str] = self._split_csv(
            os.getenv("CORS_ORIGINS_HTTP", "http://localhost:3000,http://127.0.0.1:3000")
        )
        self.cors_origins_https: List[str] = self._split_csv(
            os.getenv("CORS_ORIGINS_HTTPS", "https://localhost:3000")
        )

        # SSL (used only if use_https is true)
        self.ssl_cert_path: str = os.getenv("SSL_CERT_PATH", "./certs/cert.pem")
        self.ssl_key_path: str = os.getenv("SSL_KEY_PATH", "./certs/key.pem")

        # Pagination
        self.default_page_size: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
        self.max_page_size: int = int(os.getenv("MAX_PAGE_SIZE", "100"))

        # File Upload
        self.max_file_size: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB

    @staticmethod
    def _split_csv(value: str) -> List[str]:
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    # Helpers

    def get_database_config(self) -> dict:
        """Get database configuration details"""
        return {
            "url": self.database_url,
            "environment": self.environment,
            "debug": self.debug,
        }

    def get_cors_origins(self) -> List[str]:
        """Return protocol-aware CORS origins list"""
        return self.cors_origins_https if self.use_https else self.cors_origins_http

    def get_cors_config(self) -> dict:
        """Get CORS config dict compatible with typical middleware"""
        return {
            "allow_origins": self.get_cors_origins(),
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["*"],
        }

    def is_development(self) -> bool:
        return self.environment == "development"

    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


# Global settings instance (optional)
settings = get_settings()
