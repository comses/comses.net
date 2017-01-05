def get_first_field(obj, field_name, attribute_name='value', default=''):
    if obj[field_name]:
        return obj[field_name]['und'][0][attribute_name] or default
    else:
        return default

def get_field_attributes(json_object, field_name, attribute_name='value', default=None):
    if default is None:
        default = []
    if json_object[field_name]:
        return [obj[attribute_name] for obj in json_object[field_name]['und']]
    else:
        return default


def get_field(obj, field_name):
    if obj[field_name]:
        return obj[field_name]['und']
    else:
        return []