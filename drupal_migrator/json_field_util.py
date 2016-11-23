def get_field_first(obj, field_name, attribute_name, default=''):
    if obj[field_name]:
        return obj[field_name]['und'][0][attribute_name] or default
    else:
        return default


def get_field(obj, field_name):
    if obj[field_name]:
        return obj[field_name]['und']
    else:
        return []