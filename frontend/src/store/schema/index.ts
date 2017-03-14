import * as Ajv from 'ajv'
const job = require('json-loader!store/schema/job.json');
const search = require('json-loader!store/schema/search.json');

const ajv = new Ajv({ useDefaults: true, coerceTypes: 'array' });

export const searchSchemaValidate = ajv.compile(search);