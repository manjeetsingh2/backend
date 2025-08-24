from marshmallow import Schema, fields, validate

class VOCreateSchema(Schema):
    year = fields.Int(required=True, validate=validate.Range(min=2000, max=2100))
    season = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    village = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    crop = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    variety = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    target_area = fields.Float(required=True, validate=validate.Range(min=0.01))
    date = fields.Date(required=True)
    status = fields.Str(validate=validate.OneOf(['draft', 'submitted']), missing='draft')

class VOUpdateSchema(Schema):
    year = fields.Int(validate=validate.Range(min=2000, max=2100))
    season = fields.Str(validate=validate.Length(min=1, max=50))
    village = fields.Str(validate=validate.Length(min=1, max=100))
    crop = fields.Str(validate=validate.Length(min=1, max=100))
    variety = fields.Str(validate=validate.Length(min=1, max=100))
    target_area = fields.Float(validate=validate.Range(min=0.01))
    date = fields.Date()

class VOResponseSchema(Schema):
    id = fields.UUID()
    year = fields.Int()
    season = fields.Str()
    village = fields.Str()
    crop = fields.Str()
    variety = fields.Str()
    target_area = fields.Float()
    date = fields.Date()
    status = fields.Str()
    rejection_comments = fields.Str(allow_none=True)
    submitted_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
