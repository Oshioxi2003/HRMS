from django import template
from calendar import month_name

register = template.Library()

@register.filter
def get_month_name(month_number):
    try:
        month_number = int(month_number)
        if 1 <= month_number <= 12:
            # Dùng tiếng Việt
            month_names = {
                1: "Tháng 1", 2: "Tháng 2", 3: "Tháng 3", 4: "Tháng 4",
                5: "Tháng 5", 6: "Tháng 6", 7: "Tháng 7", 8: "Tháng 8",
                9: "Tháng 9", 10: "Tháng 10", 11: "Tháng 11", 12: "Tháng 12"
            }
            return month_names[month_number]
        return ""
    except (ValueError, TypeError):
        return ""

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary"""
    try:
        key = int(key)
        return dictionary.get(key, {})
    except (ValueError, TypeError, AttributeError):
        return {}

@register.filter
def sum_attr(queryset, attr_name):
    """Sum a specific attribute from a queryset"""
    total = 0
    for item in queryset:
        try:
            total += getattr(item, attr_name)
        except (AttributeError, TypeError):
            pass
    return total

@register.filter
def divided_by(value, arg):
    """Divide the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def split(value, arg):
    """Split the value by the argument"""
    try:
        return value.split(arg)
    except (AttributeError, ValueError):
        return [value]
