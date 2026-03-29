from django import template

register = template.Library()


@register.simple_tag
def render_hostinterface_dns(object, **context):
    output, success = object.render_dns(**context)
    return output
