import time
from collections import defaultdict, deque
from flask import request, current_app

# In-memory rate limiting (for single instance)
# For production with multiple instances, use Redis
_ip_hits = defaultdict(deque)
_user_hits = defaultdict(deque)
_register_hits = defaultdict(deque)

def _prune_old_hits(hit_queue: deque, window_sec: int, now: float):
    """Remove hits outside the time window"""
    cutoff = now - window_sec
    while hit_queue and hit_queue[0] < cutoff:
        hit_queue.popleft()

def allow_login_ip():
    """Check if login is allowed from this IP"""
    conf = current_app.config
    # Get real IP (consider X-Forwarded-For from reverse proxy)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'
    now = time.time()
    
    hit_queue = _ip_hits[client_ip]
    _prune_old_hits(hit_queue, conf['LOGIN_RATE_LIMIT_WINDOW_SEC'], now)
    
    if len(hit_queue) >= conf['LOGIN_RATE_LIMIT_PER_IP']:
        return False
    
    hit_queue.append(now)
    return True

def allow_login_user(username: str):
    """Check if login is allowed for this username"""
    conf = current_app.config
    now = time.time()
    
    hit_queue = _user_hits[username.lower()]
    _prune_old_hits(hit_queue, conf['LOGIN_RATE_LIMIT_WINDOW_SEC'], now)
    
    if len(hit_queue) >= conf['LOGIN_RATE_LIMIT_PER_USER']:
        return False
    
    hit_queue.append(now)
    return True

def allow_register_ip():
    """Check if registration is allowed from this IP"""
    conf = current_app.config
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'
    now = time.time()
    
    hit_queue = _register_hits[client_ip]
    _prune_old_hits(hit_queue, conf['REGISTER_RATE_LIMIT_WINDOW_SEC'], now)
    
    if len(hit_queue) >= conf['REGISTER_RATE_LIMIT_PER_IP']:
        return False
    
    hit_queue.append(now)
    return True
