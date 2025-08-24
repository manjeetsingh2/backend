from marshmallow import Schema, fields, validate, ValidationError, pre_load


def non_empty_string(value: str) -> str:
    """Ensure a string is non-empty after stripping whitespace."""
    if value is None:
        raise ValidationError("Field is required")
    s = value.strip()
    if not s:
        raise ValidationError("Field cannot be empty or whitespace")
    return s


class RegisterSchema(Schema):
    """
    Registration schema for creating users.
    - username: 3-80 chars, trimmed, non-empty
    - password: at least 8 chars here (stronger checks enforced in server logic)
    - role: must be VO or BO
    """
    username = fields.Str(
        required=True,
        validate=validate.And(
            validate.Length(min=3, max=80, error="Username must be 3-80 characters"),
        )
    )
    password = fields.Str(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters")
    )
    role = fields.Str(
        required=True,
        validate=validate.OneOf(["VO", "BO"], error="Role must be one of: VO, BO")
    )

    @pre_load
    def strip_inputs(self, data, **kwargs):
        """Clean and normalize input data"""
        data = dict(data or {})
        # Strip whitespace from username
        if "username" in data and isinstance(data["username"], str):
            data["username"] = data["username"].strip()
        # Normalize role to uppercase
        if "role" in data and isinstance(data["role"], str):
            data["role"] = data["role"].strip().upper()
        return data


class LoginSchema(Schema):
    """
    Login schema for authentication.
    - username: required non-empty string
    - password: required non-empty string
    """
    username = fields.Str(required=True, validate=non_empty_string)
    password = fields.Str(required=True, validate=non_empty_string)

    @pre_load
    def strip_inputs(self, data, **kwargs):
        """Clean input data"""
        data = dict(data or {})
        if "username" in data and isinstance(data["username"], str):
            data["username"] = data["username"].strip()
        return data


class RefreshTokenSchema(Schema):
    """Schema for token refresh requests (optional - for future use)"""
    refresh_token = fields.Str(required=True, validate=non_empty_string)


class ChangePasswordSchema(Schema):
    """
    Schema for password change requests (optional - for future use)
    - old_password: required
    - new_password: at least 8 chars here (stronger checks enforced in server logic)
    """
    old_password = fields.Str(required=True, validate=non_empty_string, load_only=True)
    new_password = fields.Str(
        required=True,
        validate=validate.Length(min=8, error="New password must be at least 8 characters"),
        load_only=True
    )

    @pre_load
    def strip_inputs(self, data, **kwargs):
        """Clean input data"""
        return dict(data or {})


class ForgotPasswordSchema(Schema):
    """Schema for forgot password requests (optional - for future use)"""
    username = fields.Str(required=True, validate=non_empty_string)

    @pre_load
    def strip_inputs(self, data, **kwargs):
        """Clean input data"""
        data = dict(data or {})
        if "username" in data and isinstance(data["username"], str):
            data["username"] = data["username"].strip()
        return data


class ResetPasswordSchema(Schema):
    """Schema for password reset requests (optional - for future use)"""
    reset_token = fields.Str(required=True, validate=non_empty_string)
    new_password = fields.Str(
        required=True,
        validate=validate.Length(min=8, error="New password must be at least 8 characters"),
        load_only=True
    )

    @pre_load
    def strip_inputs(self, data, **kwargs):
        """Clean input data"""
        return dict(data or {})
