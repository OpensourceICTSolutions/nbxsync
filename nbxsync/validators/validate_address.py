from django.core.exceptions import ValidationError
from django.core.validators import validate_domain_name, validate_ipv46_address


def validate_address(address):
    try:
        validate_domain_name(address)
    except ValidationError:
        try:
            validate_ipv46_address(address)
        except ValidationError:
            raise ValidationError(f"'{address}' is neither a valid domain name nor an IP address.")
