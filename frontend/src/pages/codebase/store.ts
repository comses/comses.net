import * as Vue from 'vue'
import Vuex from 'vuex'
import { CodebaseReleaseEdit, CodebaseContributor } from '../../store/common'
import { api_base } from '../../api/index'
import * as _ from 'lodash'
import axios from 'axios'
import * as yup from 'yup'

const initialState: CodebaseReleaseEdit = {
    files: {
        sources: { upload_url: '', files: [] },
        data: { upload_url: '', files: [] },
        documentation: { upload_url: '', files: [] },
    },
    validation_errors: {
        codebase: {
            title: [],
            description: [],
            live: [],
            is_replication: [],
            tags: [],
            repository_url: []
        },
        description: [],
        embargo_end_date: [],
        os: [],
        platforms: [],
        programming_languages: [],
        live: [],
        licence: []
    },
    codebase: {
        associatiated_publications_text: '',
        description: '',
        doi: null,
        featured: false,
        first_published_on: '2006-01-01',
        has_published_changes: false,
        identifier: '',
        is_replication: false,
        keywords: [],
        last_published_on: '2006-01-01',
        latest_version: null,
        live: false,
        peer_reviewed: false,
        references_text: '',
        relationships: {},
        repository_url: '',
        submitter: {
            family_name: '',
            given_name: '',
            username: ''
        },
        summary: '',
        tags: [],
        title: ''
    },
    release_contributors: [],
    dependencies: [],
    description: '',
    documentation: '',
    doi: null,
    embargo_end_date: null,
    licence: '',
    live: false,
    os: '',
    peer_reviewed: false,
    platforms: [],
    programming_languages: [],
    submitted_package: '',
    submitter: {
        family_name: '',
        given_name: '',
        username: ''
    },
    version_number: ''
};

const schema = yup.object().shape({
    codebase: yup.object().shape({
        title: yup.string().required().label('Title'),
        description: yup.string().required().min(20),
        live: yup.bool().label('Is Published?'),
        is_replication: yup.bool(),
        repository_url: yup.string().url()
    }),
    description: yup.string().required(),
    embargo_end_date: yup.date(),
    os: yup.string().required(),
    platforms: yup.array().of(yup.string()),
    programming_languages: yup.array().of(yup.string()),
    live: yup.bool(),
    licence: yup.string().required()
})

function pathToCamelCase(path: string): string {
    return _.camelCase(path);
}

const pathToComputedName = pathToCamelCase;

export function exposeComputed(paths: Array<string>): object {
    let computed = {};
    paths.forEach(function (path) {
        let computed_name = pathToComputedName(path);
        let error_name = `${computed_name}Errors`
        computed[computed_name] = {
            get: function () {
                return _.get(this.$store.state, path);
            },
            set: function (value) {
                this.$store.dispatch('setAtPath', {path, value});
            }
        }
        computed[error_name] = {
            get: function() {
                const errorMsg = _.get(this.$store.state.validation_errors, path);
                return errorMsg ? errorMsg : []
            }
        }
    });
    return computed;
}

export const store = {
    state: { ...initialState },
    mutations: {
        setCodebaseReleaseAtPath(state, {path, value}) {
            _.set(state, path, value);
        },
        setValidationErrorAtPath(state, {path, value}) {
            _.set(state.validation_errors, path, value);
        },
        unsetValidationErrorAtPath(state, path) {
            _.set(state.validation_errors, path, []);
        },
        setFiles(state, {upload_type, value}) {
            state.files[upload_type] = value;
        },
        setCodebaseRelease(state, data) {
            Object.keys(state).forEach(
                function (k) {
                    if (data[k] !== undefined) {
                        state[k] = data[k];
                    }
                });
            state.release_contributors.forEach(v => {
                v._id = _.uniqueId();
            });
        },
        upsertReleaseContributor(state, release_contributor: CodebaseContributor) {
            const ind = _.findIndex(state.release_contributors, rc => release_contributor._id === rc._id);
            if (ind !== -1) {
                state.release_contributors[ind] = _.extend({}, release_contributor);
            } else {
                console.log(state);
                state.release_contributors.push(_.extend({}, release_contributor));
            }
        },
        deleteReleaseContributor(state, _id: string) {
            const index = _.findIndex(state.release_contributors, rc => rc._id === _id);
            state.release_contributors.splice(index, 1);
        }
    },
    actions: {
        getCodebaseRelease(context, { identifier, version_number }) {
            return api_base.get(`/codebases/${identifier}/releases/${version_number}/`).then(
                response => context.commit('setCodebaseRelease', response.data));
        },

        setAtPath(context, { path, value }) {
            context.commit('setCodebaseReleaseAtPath', {path, value});
            const schema_path = path.replace('.', '.fields.');
            const subSchema = _.get(schema.fields, schema_path);
            context.dispatch('setErrorsAtPath', {schema: subSchema, path, value});
        },

        // Calculate any validation errors after 1s wait
        setErrorsAtPath: _.debounce((context, { schema, path, value}) => schema.validate(value).then(
                value => context.commit('unsetValidationErrorAtPath', path), 
                validation_error => context.commit('setValidationErrorAtPath', { path, value: validation_error.errors })), 800),

        getFiles(context, upload_type) {
            return api_base.get(`/codebases/${context.state.codebase.identifier}/releases/${context.state.version_number}/${upload_type}/`).then(
                response => context.commit('setFiles', {upload_type, value: response.data}));
        },

        deleteFile(context, { upload_type, path}: {upload_type: string, path: string}) {
            api_base.delete(path).then(response => context.commit('setFiles', {upload_type, value: response.data}));
        },

        initialize(context, { identifier, version_number }) {
            return context.dispatch('getCodebaseRelease', { identifier, version_number }).then(
                r => axios.all([context.dispatch('getFiles', 'data'), context.dispatch('getFiles', 'documentation'), context.dispatch('getFiles', 'sources')]));
        },

        submit(context) {
            return api_base.put(`/codebases/${context.state.codebase.identifier}/releases/${context.state.version_number}/`, context.state);
        }
    }
};