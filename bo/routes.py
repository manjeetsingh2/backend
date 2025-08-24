from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from app.utils import require_role, safe_execute, success_response, error_response, paginated_response, get_pagination_params
from bo.services import BOService
from bo.schemas import BOApprovalSchema, BOResponseSchema

bo_bp = Blueprint('bo', __name__, url_prefix='/api/v1/bo')
bo_service = BOService()

@bo_bp.route('/crop-targets/pending', methods=['GET'])
@require_role(['BO'])
@safe_execute
def get_pending_approvals():
    page, per_page = get_pagination_params()
    
    filters = {
        'year': request.args.get('year', type=int),
        'village': request.args.get('village'),
        'crop': request.args.get('crop'),
        'season': request.args.get('season'),
        'variety': request.args.get('variety')
    }
    
    query = bo_service.get_pending_query(filters)
    return paginated_response(query, page, per_page, BOResponseSchema)

@bo_bp.route('/crop-targets/<uuid:crop_target_id>/approve', methods=['PUT'])
@require_role(['BO'])
@safe_execute
def approve_crop_target(crop_target_id):
    try:
        schema = BOApprovalSchema()
        data = schema.load(request.get_json() or {})
        approver_id = get_jwt_identity()
        
        result = bo_service.approve_crop_target(crop_target_id, data, approver_id)
        status = data['status']
        return success_response(result, f"Crop target {status} successfully")
    except ValidationError as e:
        return error_response("Invalid input data", 400, e.messages)

@bo_bp.route('/dashboard/summary', methods=['GET'])
@require_role(['BO'])
@safe_execute
def get_summary():
    filters = {
        'year': request.args.get('year', type=int),
        'season': request.args.get('season')
    }
    
    summary = bo_service.get_summary(filters)
    return success_response(summary)
