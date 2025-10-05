import ast

from django import forms


class MultiIPWidget(forms.Widget):
    template_name = 'nbxsync/widgets/multi_ip_widget.html'

    def format_value(self, value):
        if isinstance(value, str):
            try:
                parsed = ast.literal_eval(value)
                if isinstance(parsed, list):
                    return [str(v).strip() for v in parsed if str(v).strip()]
            except (ValueError, SyntaxError):
                return [v.strip() for v in value.split(',') if v.strip()]
        elif isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return []

    def value_from_datadict(self, data, files, name):
        return [v.strip() for v in data.getlist(name) if v.strip()]
