from beyo_manager.errors.validation import ValidationError

_MIN_PASSWORD_LENGTH = 8


def validate_password_policy(password: str) -> None:
    if len(password) < _MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters long.")
