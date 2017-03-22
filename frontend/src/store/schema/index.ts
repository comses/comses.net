import * as Ajv from 'ajv'
const search = {
  "id": "/search",
  "title": "Search",
  "type": "object",
  "properties": {
    "query": { "type": "string", "default": ""},
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "default": []
    }
  },
  "required": ["query", "tags"]
};

const ajv = new Ajv({ useDefaults: true, coerceTypes: 'array' });

export const searchSchemaValidate = ajv.compile(search);