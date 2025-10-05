from django import template

register = template.Library()


@register.filter
def render_field(obj, field_name):
    output, success = obj.render_field(field_name)
    return output
