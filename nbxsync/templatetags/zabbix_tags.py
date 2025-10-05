from django import template

register = template.Library()


@register.simple_tag
def render_zabbix_tag_assignment(assignment, **context):
    output, success = assignment.render(**context)
    return output
