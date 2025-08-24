from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from app.utils import require_role, safe_execute, success_response, error_response, paginated_response, get_pagination_params
from vo.services import VOService
from vo.schemas import VOCreateSchema, VOUpdateSchema, VOResponseSchema

vo_bp = Blueprint('vo', __name__, url_prefix='/api/v1/vo')
vo_service = VOService()

@vo_bp.route('/crop-targets', methods=['POST'])
@require_role(['VO'])
@safe_execute
def create_crop_target():
    try:
        schema = VOCreateSchema()
        data = schema.load(request.get_json() or {})
        user_id = get_jwt_identity()
        
        result = vo_service.create_crop_target(data, user_id)
        return success_response(result, "Crop target created successfully", 201)
    except ValidationError as e:
        return error_response("Invalid input data", 400, e.messages)

@vo_bp.route('/crop-targets/my-submissions', methods=['GET'])
@require_role(['VO'])
@safe_execute
def get_my_submissions():
    user_id = get_jwt_identity()
    page, per_page = get_pagination_params()
    
    # Extract filters
    filters = {
        'year': request.args.get('year', type=int),
        'status': request.args.get('status'),
        'crop': request.args.get('crop'),
        'village': request.args.get('village'),
        'season': request.args.get('season'),
        'variety': request.args.get('variety')
    }
    
    query = vo_service.get_my_submissions_query(user_id, filters)
    return paginated_response(query, page, per_page, VOResponseSchema)

@vo_bp.route('/crop-targets/<uuid:crop_target_id>', methods=['GET'])
@require_role(['VO'])
@safe_execute
def get_crop_target(crop_target_id):
    user_id = get_jwt_identity()
    crop_target = vo_service.get_crop_target_by_id(crop_target_id, user_id)
    
    schema = VOResponseSchema()
    result = schema.dump(crop_target)
    return success_response(result)

@vo_bp.route('/crop-targets/<uuid:crop_target_id>', methods=['PUT'])
@require_role(['VO'])
@safe_execute
def update_crop_target(crop_target_id):
    try:
        user_id = get_jwt_identity()
        schema = VOUpdateSchema()
        data = schema.load(request.get_json() or {})
        
        result = vo_service.update_crop_target(crop_target_id, data, user_id)
        return success_response(result, "Crop target updated successfully")
    except ValidationError as e:
        return error_response("Invalid input data", 400, e.messages)

@vo_bp.route('/crop-targets/<uuid:crop_target_id>/resubmit', methods=['POST'])
@require_role(['VO'])
@safe_execute
def resubmit_crop_target(crop_target_id):
    user_id = get_jwt_identity()
    result = vo_service.resubmit_crop_target(crop_target_id, user_id)
    return success_response(result, "Crop target resubmitted successfully")

@vo_bp.route('/crop-targets/<uuid:crop_target_id>', methods=['DELETE'])
@require_role(['VO'])
@safe_execute
def delete_crop_target(crop_target_id):
    user_id = get_jwt_identity()
    vo_service.delete_crop_target(crop_target_id, user_id)
    return success_response(message="Crop target deleted successfully")

@vo_bp.route('/dashboard/summary', methods=['GET'])
@require_role(['VO'])
@safe_execute
def get_summary():
    user_id = get_jwt_identity()
    year = request.args.get('year', type=int)
    season = request.args.get('season')
    
    summary = vo_service.get_summary(user_id, year, season)
    return success_response(summary)
