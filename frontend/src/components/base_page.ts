import {rootCreateRecord, rootUpdateRecord, rootRetrieveRecord, relatedRetrieveRecord} from 'api/index'

export const basePageMixin: any = {
        methods: {
            context() {
                let self = this;
                return {
                    data: (value) => self.data = value,
                    validationErrors: (value) => self.validationErrors = value,
                    mainError: (value) => self.mainError = value
                };
            },

            create(createUrl: string) {
                return rootCreateRecord(this.context(), createUrl, this.data);
            },

            update(updateUrl: string) {
                return rootUpdateRecord(this.context(), updateUrl, this.data);
            },

            retrieve(retrieveUrl: string) {
                return rootRetrieveRecord(this.context(), retrieveUrl);
            },

            setField(content_key, field_key: 'value' | 'errors', value) {
                let content = this.state.content;
                if (content[content_key] === undefined) {
                    content[content_key] = {value, errors: []}
                } else {
                    content[content_key][field_key] = value
                }
            }
        },
        computed: {
            mainErrorMessage: {
                get: function () {
                    this.state.mainError.join('. ');
                }
            },
            data: {
                get: function () {
                    let value: any = {};
                    for (const k in this.state.content) {
                        value[k] = this.state.content[k].value;
                    }
                    return value;
                },
                set: function (obj) {
                    for (const k in obj) {
                        this.setField(k, 'value', obj[k])
                    }
                }
            },
            validationErrors: {
                get: function () {
                    let errors: any = {};
                    for (const k in this.state.content) {
                        errors[k] = this.state.content[k].errors;
                    }
                    return errors;
                },
                set: function (obj) {
                    for (const k in obj) {
                        this.setField(k, 'errors', obj[k])
                    }
                }
            },
            mainError: {
                get: function () {
                    return this.state.mainError;
                },
                set: function (obj) {
                    this.state.mainError = obj;
                }
            }
        }
    };