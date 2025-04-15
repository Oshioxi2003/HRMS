# templatetags/report_filters.py
from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter
def currency(value):
    """Format a number as currency"""
    try:
        value = float(value)
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return value

@register.filter
def percentage(value):
    """Format a number as percentage"""
    try:
        value = float(value)
        return f"{value:.2f}%"
    except (ValueError, TypeError):
        return value

@register.filter
def attendance_rate_color(rate):
    """Return a color class based on attendance rate"""
    try:
        rate = float(rate)
        if rate >= 90:
            return 'success'
        elif rate >= 75:
            return 'info'
        elif rate >= 60:
            return 'warning'
        else:
            return 'danger'
    except (ValueError, TypeError):
        return 'secondary'

@register.filter
def dictsumattr(data, attr):
    """Sum a specific attribute from a list of dictionaries"""
    try:
        return sum(item.get(attr, 0) for item in data)
    except (TypeError, AttributeError):
        return 0

@register.filter
def dictavgattr(data, attr):
    """Average a specific attribute from a list of dictionaries"""
    try:
        values = [item.get(attr, 0) for item in data]
        return sum(values) / len(values) if values else 0
    except (TypeError, AttributeError, ZeroDivisionError):
        return 0

@register.filter
def to_json(value):
    """Convert a Python object to JSON string"""
    return mark_safe(json.dumps(value))
