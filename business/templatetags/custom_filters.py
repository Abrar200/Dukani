from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_opening_hour(opening_hours, day):
    return opening_hours.filter(day=day).first()

@register.filter
def to(value, arg):
    return range(int(value), int(arg))

@register.filter
def subtract_from(value, arg):
    return int(arg) - int(value)

@register.filter
def times(value):
    return range(int(value))

@register.filter
def to(value, arg):
    """
    Returns a range from value to arg.
    Ensures that value and arg are integers before creating the range.
    """
    value = int(value)
    arg = int(arg)
    return range(value, arg)

@register.filter
def subtract(value, arg):
    """Subtracts arg from value, ensuring both are integers."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return ''