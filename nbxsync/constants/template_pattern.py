import re

TEMPLATE_PATTERN = re.compile(r'({{.*?}}|{%-?\s*.*?\s*-?%}|{#.*?#})')
