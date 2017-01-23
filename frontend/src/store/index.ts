import * as Vue from 'vue'
import * as Vuex from 'vuex'

import { actions } from './actions'
import { mutations } from './mutations'
import * as types from './types'

import {StoreOptions} from "vuex";
import {ActionContext} from "vuex";
import {State} from "./types";
import {Store} from "vuex";

Vue.use(Vuex);

export const initialState: types.State = {
    job: {
        detail: {
            id: -1,
            title: '',
            url: '',
            date_created: '',
            submitter: {
                username: '',
                last_name: '',
                first_name: ''
            },
            description: ''
        },
        page: {
            count: 0,
            n_pages: 0,
            page_ind: 0,
            query: '',
            range: [],
            results: []
        },
        search: ''
    },
    user: {
        username: 'calvin',
        last_name: '',
        first_name: ''
    },
    codebase: {
        title: '',
        description: '',
        doi: '',
        live: false,
        is_replication: false,
        keywords: [],
        contributors: []
    }
};

export default new Vuex.Store(<StoreOptions<State>>{
    actions,
    mutations,
    getters: {
        pagination: state => {
            const { n_pages, page_ind, query } = state.job.page;
            return { n_pages, page_ind, query }
        },
        jobs: state => state.job.page.results,
        job_detail: state => state.job.detail,
        job_query: state => state.job.search
    },
    state: { ...initialState },
    strict: true
});