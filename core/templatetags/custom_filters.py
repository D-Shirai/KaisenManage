from django import template

register = template.Library()

@register.filter
def strip_tou(room_number):
    if '-' in room_number:
        return room_number.split('-', 1)[1]
    return room_number
