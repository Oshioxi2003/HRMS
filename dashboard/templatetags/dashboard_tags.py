from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def div(value, arg):
    """
    Divides the value by the argument
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """
    Multiplies the value by the argument
    """
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0

@register.filter
def subtract(value, arg):
    """
    Subtracts the argument from the value
    """
    try:
        return float(value) - float(arg)
    except ValueError:
        return 0

@register.filter
def percentage(value, arg):
    """
    Calculates the percentage of value/arg
    """
    try:
        return (float(value) / float(arg)) * 100
    except (ValueError, ZeroDivisionError):
        return 0
