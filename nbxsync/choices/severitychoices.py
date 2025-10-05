# choices/severitychoices.py
from django.db import models


class SeverityChoices(models.IntegerChoices):
    NOT_CLASSIFIED = 0, 'Not classified'
    INFORMATION = 1, 'Information'
    WARNING = 2, 'Warning'
    AVERAGE = 3, 'Average'
    HIGH = 4, 'High'
    DISASTER = 5, 'Disaster'


SEVERITY_CSS = {
    SeverityChoices.NOT_CLASSIFIED: 'secondary',
    SeverityChoices.INFORMATION: 'info',
    SeverityChoices.WARNING: 'warning',
    SeverityChoices.AVERAGE: 'primary',
    SeverityChoices.HIGH: 'danger',
    SeverityChoices.DISASTER: 'danger',
}


def severity_css(value_or_member, default='secondary'):
    member = value_or_member if isinstance(value_or_member, SeverityChoices) else SeverityChoices(value_or_member)
    return SEVERITY_CSS.get(member, default)
