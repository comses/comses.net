import * as _ from 'lodash';
import * as yup from 'yup';

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

function createComputed(key: string, validate: (self, value) => Promise<any>) {
    const debouncedValidator = _.debounce((self, value) => validate(self, value)
        .catch(() => {}), 500);
    return {
        get: function () {
            return this.state[key];
        },
        set: function (value) {
            this.state[key] = value;
            debouncedValidator(this, value);
        }
    }
}

function createDefaultErrors(keys) {
    const errors = {};
    keys.forEach(key => {
        errors[key] = [];
    });
    return errors;
}

function createFieldValidator(schema, key: string) {

    return async function validator(self, value) {
        const subSchema = yup.reach(schema, key);
        try {
            const v = await subSchema.validate(value);
            self.errors[key] = [];
            return v;
        } catch(e) {
            if (e.errors) {
                self.errors[key] = e.errors;
                return Promise.reject(e);
            }
        }
    };
}

export function createFormValidator(schema) {
    const defaultValue = createDefaultValue(schema);
    const keys = Object.keys(schema.fields);
    const defaultErrors = createDefaultErrors(keys);
    const computed = {};
    const $validators = _.transform(keys, (validators, key) => {
        const validator = createFieldValidator(schema, key);
        computed[key] = createComputed(key, validator);
        validators[key] = validator;
    }, {});

    let vueOptions = {
        data() {
            return {
                state: defaultValue,
                errors: defaultErrors
            }
        },
        computed,
        methods: {
            validate() {
                const validationResults = _.chain(this.$options.$validators).toPairs()
                    .map(([k,v]) => v(this, this[k])).value();
                return Promise.all(validationResults);
            },
            clear() {
                keys.forEach(key => this.errors[key] = []);
            },
            replace(state) {
                this.clear();
                this.state = state;
            }
        },
        $validators
    };

    return vueOptions;
}

function retrieve(schema, retrieveAPI) {
    return async function() {

    }
}