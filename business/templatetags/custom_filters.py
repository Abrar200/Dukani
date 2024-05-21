from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Returns the value from a dictionary for the given key.
    If the key doesn't exist, returns an empty string.
    """
    return dictionary.get(key, '')