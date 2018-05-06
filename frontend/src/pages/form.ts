import * as _ from 'lodash';
import yup from 'yup';
import Vue from 'vue'
import {VueClass} from 'vue-class-component/lib/declarations'
import {Component} from 'vue-property-decorator'

const yupDefaultFormDispatch = {
    [yup.object().constructor]: (schema) => {
        let default_value: object = {};
        for (const field_name in schema.fields) {
            const subSchema = schema.fields[field_name];
            default_value[field_name] = createDefaultValue(subSchema);
        }
        return default_value;
    },
    [yup.string().constructor]: (schema) => '',
    [yup.boolean().constructor]: (schema) => false,
    [yup.date().constructor]: (schema) => {
        if (schema._nullable === true) {
            return null;
        } else {
            return (new Date()).toISOString();
        }
    },
    [yup.array().constructor]: (schema) => [],
    [yup.mixed().constructor]: (schema) => {
        const whitelist_values = schema._whitelist._map;
        if (!_.isEmpty(whitelist_values)) {
            return whitelist_values[Object.keys(whitelist_values)[0]];
        } else {
            return null;
        }
    }
};

export function createDefaultValue(schema) {
    /**
     * convert a yup schema into a plain js default value for Vue
     */
    if (schema._default !== undefined) {
        return schema._default;
    }
    if (schema.constructor in yupDefaultFormDispatch) {
        return yupDefaultFormDispatch[schema.constructor](schema);
    } else {
        throw new Error(`invalid schema type: ${schema.constructor.name}`)
    }
}

function createFormControlConfig(schema) {
    const config = {};
    for (const field_name in schema.fields) {
        const field = schema.fields[field_name];
        config[field_name] = false;
        for (const test of field.tests) {
            if (test.TEST_NAME === 'is-not-null') {
                break;
            }
            if (test.TEST_NAME === 'required') {
                config[field_name] = true;
                break;
            }
        }
    }
    return config;
}

function createComputed(key: string, validate: (self, value) => Promise<any>) {
    const debouncedValidator = _.debounce((self, value) => validate(self, value)
        .catch(() => {
        }), 500);
    return {
        get: function () {
            return (<any>this).state[key];
        },
        set: function (value) {
            (<any>this).state[key] = value;
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

export function populateErrorsFromValidationError(self, ve) {
    const errors = ve.inner;
    if (!_.isNil(ve.path)) {
        self.errors[ve.path] = [];
        self.errors[ve.path].push(ve.message);
    }
    for (const error of errors) {
        self.errors[error.path] = [error.message];
    }
    self.statusMessages = [{
        classNames: 'alert alert-warning',
        message: 'Form not submitted. Please check above for validation errors.'
    }];
}

export function reachRelated(schema, key) {
    const shape = {};
    const subSchema = yup.reach(schema, key);
    shape[key] = subSchema;

    const dependentKeys: Array<string> = subSchema._deps;
    for (const dependentKey of dependentKeys) {
        const dependentSchema = yup.reach(schema, dependentKey).clone();
        dependentSchema._conditions = [];
        dependentSchema._deps = [];
        shape[dependentKey] = dependentSchema;
    }
    return yup.object().shape(shape);
}

function createFieldValidator(schema, key: string) {
    const subSchema = reachRelated(schema, key);
    return async function validator(self, value) {
        try {
            const v = await subSchema.validate(self.state);
            self.errors[key] = [];
            return v;
        } catch (e) {
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
    const formControlConfig = createFormControlConfig(schema);

    const computed = {};
    const $validators = _.transform(keys, (validators, key) => {
        const validator = createFieldValidator(schema, key);
        computed[key] = createComputed(key, validator);
        validators[key] = validator;
    }, {});

    @Component(<any>{
        computed,
        $validators
    })
    class FormValidator extends Vue {
        statusMessages: Array<{ classNames: string, message: string }> = [];
        state = defaultValue;
        errors = defaultErrors;
        config = formControlConfig;

        async validate() {
            try {
                const state = await schema.validate(this.state, {abortEarly: false});
            } catch (validationErrors) {
                populateErrorsFromValidationError(this, validationErrors);
                throw validationErrors;
            }
        }

        clear() {
            keys.forEach(key => this.errors[key] = []);
        }

        replace(state) {
            this.clear();
            this.state = state;
        }
    }

    return FormValidator;
}
