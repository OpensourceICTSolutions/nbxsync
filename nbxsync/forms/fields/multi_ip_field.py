from django import forms


class MultiIPField(forms.Field):
    def to_python(self, value):
        if not value:
            return []

        if isinstance(value, str):
            return [v.strip() for v in value.split(',') if v.strip()]
        if isinstance(value, list):
            return [v.strip() for v in value if v.strip()]
        return []

    def validate(self, value):
        super().validate(value)
