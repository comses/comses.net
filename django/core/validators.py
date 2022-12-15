from django.core.exceptions import ValidationError
import jsonschema


def validate_affiliations(value):
    AFFILIATIONS_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "url": {"type": "string", "format": "uri", "pattern": "^https?://"},
                "acronym": {"type": "string"},
                "ror_id": {
                    "type": "string",
                    "format": "uri",
                    "pattern": "^https?://ror.org/",
                },
            },
            "required": ["name"],
        },
    }

    try:
        jsonschema.validate(value, AFFILIATIONS_SCHEMA)
        # make sure all affiliation names are unique
        if not len(set([affil["name"] for affil in value])) == len(value):
            raise ValidationError("Affiliation name must be unique")
    except Exception as e:
        # FIXME: give a better error message
        raise ValidationError(e)
    return value
