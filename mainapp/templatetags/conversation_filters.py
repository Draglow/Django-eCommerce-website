from django import template

register = template.Library()

@register.filter
def filter_messages(messages, user):
    return len([msg for msg in messages if not msg.is_read and msg.sender != user]) 