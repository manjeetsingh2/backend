from marshmallow import Schema, fields, validate, validates_schema, ValidationError

class BOApprovalSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(['approved', 'rejected']))
    rejection_comments = fields.Str(allow_none=True, validate=validate.Length(max=1000))
    
    @validates_schema
    def validate_rejection(self, data, **kwargs):
        if data.get('status') == 'rejected' and not data.get('rejection_comments'):
            raise ValidationError('Rejection comments required when rejecting')

class BOResponseSchema(Schema):
    id = fields.UUID()
    year = fields.Int()
    season = fields.Str()
    village = fields.Str()
    crop = fields.Str()
    variety = fields.Str()
    target_area = fields.Float()
    date = fields.Date()
    status = fields.Str()
    submitted_by = fields.Str()
    submitted_at = fields.DateTime()
    rejection_comments = fields.Str(allow_none=True)
    approved_by = fields.Str(allow_none=True)
    approved_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime()
