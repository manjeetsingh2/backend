# In any file, test the config
from app.config import get_current_config, print_config_info

config = get_current_config()
print(f"CORS Origins: {config.CORS_ORIGINS}")
print(f"Security Headers: {config.get_security_headers()}")

# Or print full info
print_config_info()
