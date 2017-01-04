import * as Vue from 'vue'
import * as Vuex from 'vuex'

import actions from './actions'
import mutations from './mutations'
import * as types from './types'

import {StoreOptions} from "vuex";

Vue.use(Vuex);

const initialState: types.State = {
    job: {
        detail: {
            id: -1,
            title: '',
            url: '',
            date_created: '',
            creator: { username: ''},
            content: ''
        },
        list: {
            count: 0,
            n_pages: 0,
            page_ind: 0,
            query: '',
            range: [],
            results: []
        },
        search: ''
    }
};

export default new Vuex.Store({
    actions,
    mutations,
    getters: {
        pagination: state => {
            const { n_pages, page_ind, query } = state.job.list;
            return { n_pages, page_ind, query }
        },
        jobs: state => state.job.list.results,
        job_detail: state => state.job.detail,
        job_query: state => state.job.search
    },
    state: { ...initialState },
    strict: true
});