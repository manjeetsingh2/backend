from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Response helpers (DRY)
def success_response(data=None, message="Success", status=200):
    response = {"success": True, "message": message}
    if data:
        response["data"] = data
    return jsonify(response), status

def error_response(message="Error", status=400, errors=None):
    response = {"success": False, "message": message}
    if errors:
        response["errors"] = errors
    return jsonify(response), status

# Pagination helper (DRY)
def get_pagination_params():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    return max(1, page), max(1, per_page)

def paginated_response(query, page, per_page, schema):
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = schema(many=True).dump(pagination.items)
    
    meta = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.next_num if pagination.has_next else None,
        "prev_page": pagination.prev_num if pagination.has_prev else None
    }
    
    return success_response({
        "items": items,
        "pagination": meta
    })

# Auth decorator (DRY)
def require_role(allowed_roles):
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            role = claims.get("role")
            if role not in allowed_roles:
                return error_response("Access denied", 403)
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Safe execution wrapper (Error-free)
def safe_execute(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return error_response(str(e), 400)
        except Exception as e:
            logger.exception(f"Error in {f.__name__}")
            return error_response("Internal server error", 500)
    return wrapper
