import * as Vue from 'vue'
import Vuex from 'vuex'
import { CodebaseReleaseEdit, CodebaseContributor } from '../../store/common'
import { api_base } from '../../api/index'
import * as _ from 'lodash'
import axios from 'axios'

const initialState: CodebaseReleaseEdit = {
    files: {
        sources: { upload_url: '', files: [] },
        data: { upload_url: '', files: [] },
        documentation: { upload_url: '', files: [] },
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

const validations = {
    // codebaseAssociatiatedPublicationsText: '',
    // codebaseDescription: '',
    // // codebaseFirstPublishedOn: '2006-01-01',
    // codebaseHasPublishedChanges: false,
    // codebaseIdentifier: '',
    // codebseIsReplication: false,
    // codebaseKeywords: [],
    // // codebaseLastPublishedOn: '2006-01-01',
    // // latest_version: null,
    // // live: false,
    // // codebasePeerReviewed: false,
    // codebaseReferencesText: '',
    // codebaseRelationships: {},
    // codebaseRepositoryUrl: '',
    //     // submitter: {
    //     //     family_name: '',
    //     //     given_name: '',
    //     //     username: ''
    //     // },
    // codebaseSummary: '',
    // codebaseTags: [],
    // codebaseTitle: '',

    // codebaseContributors: '',

    dependencies: 'required',
    description: 'required',
    documentation: 'required',
    embargoEndDate: 'required',
    licence: 'required',
    live: '',
    os: 'required',
    // peerReviewed: '',
    platforms: 'required',
    programmingLanguages: 'required'
}

function pathToCamelCase(path: string): string {
    return _.camelCase(path);
}

const pathToComputedName = pathToCamelCase;

export function exposeComputed(paths: Array<string>): object {
    let computed = {};
    paths.forEach(function (path) {
        let computed_name = pathToComputedName(path);
        computed[computed_name] = {
            get: function () {
                return _.get(this.$store.state, path);
            },
            set: function (value) {
                this.$store.commit('setCodebaseReleaseAtPath', {path, value});
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

        // updateCodebaseRelease(context) {
        //     return api_base.put(`/codebases/${context.state.codebase.identifier}/releases/${context.state.version_number}/`, context.state).then(
        //         response => context.dispatch('getCodebaseRelease', { identifier: context.state.identifier, version_number: context.state.version_number }))
        // },

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
        }
    }
};