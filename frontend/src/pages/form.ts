import * as _ from 'lodash';
import * as yup from 'yup';

interface FormData {
    errorAttributeName: string
    stateAttributeName: string
}

interface Methods {
    validationMethodName: string
    clearErrorsMethodName: string
}

export function createDefaultValue(schema) {
    switch (schema.constructor.name) {
        case 'ObjectSchema': {
            let default_value: object = {};
            for (const field_name in schema.fields) {
                const subSchema = schema.fields[field_name];
                default_value[field_name] = createDefaultValue(subSchema);
            }
            return default_value;
        }
        case 'StringSchema':
            return '';
        case 'BooleanSchema':
            return false;
        case 'DateSchema': {
            if (schema._nullable === true) {
                return null;
            } else {
                return (new Date()).toISOString();
            }
        }
        case 'ArraySchema':
            return [];
        case 'SchemaType': {
            const whitelist_values = schema._whitelist._map;
            if (!_.isEmpty(whitelist_values)) {
                return whitelist_values[Object.keys(whitelist_values)[0]];
            } else {
                return null;
            }
        }
        default:
            throw new Error(`invalid schema type: ${schema.constructor.name}`)
    }
}

function createFieldValidator(schema, path: string, data: FormData, vueOptions) {

    const validator = function (self, value) {
        const subSchema = yup.reach(schema, path);
        return subSchema.validate(value)
            .then(function (value) {
                _.set(self, `${data.errorAttributeName}.${path}`, []);
                return Promise.resolve(value);
            })
            .catch(function (ve) {
                _.set(self, `${data.errorAttributeName}.${path}`, ve.errors)
                return Promise.reject(ve);
            });
    };

    const debouncedValidator = _.debounce((self, value) => validator(self, value).catch(() => {
    }), 500);

    _.set(vueOptions, `data.${data.errorAttributeName}.${path}`, []);

    vueOptions.watch[`${data.stateAttributeName}.${path}`] = function (value) {
        debouncedValidator.cancel();
        return debouncedValidator(this, value)
    };

    const globalValidator = self => validator(self, _.get(self, `${data.stateAttributeName}.${path}`));

    return globalValidator;
}

export function createFormValidator(schema, data: FormData, methods: Methods) {
    let vueOptions: { data: object, watch: object, methods: object } = {
        data: {},
        watch: {},
        methods: {}
    };
    vueOptions.data[data.stateAttributeName] = createDefaultValue(schema);

    const validators = Object.keys(schema.fields).map(function (path) {
        return createFieldValidator(schema, path, data, vueOptions);
    });

    const _data = _.merge({}, vueOptions.data);
    vueOptions.data = function () {
        return _data;
    };
    vueOptions.methods[methods.validationMethodName] = function () {
        const validationResults = validators.map(v => v(this));
        return Promise.all(validationResults);
    };

    vueOptions.methods[methods.clearErrorsMethodName] = function () {
        Object.keys(_data[data.errorAttributeName]).forEach(key => this[data.errorAttributeName][key] = []);
    };

    return vueOptions;
}