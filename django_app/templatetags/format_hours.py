from django import template

register = template.Library()


@register.filter
def format_hours(value):
    """Remove ,0 and .0 from value."""
    try:
        v = float(value)
        if v.is_integer():
            return int(v)
        return v
    except:
        return value
