import * as Vue from 'vue'
import * as Vuex from 'vuex'

import { Codebase, Job, ViewSet } from './common'

Vue.use(Vuex);

const job: Job = {
    description: '',
    title: ''
};

const codebase: Codebase = {
            title: '',
            description: '',
            doi: null,
            live: false,
            is_replication: false,
            keywords: [],
            contributors: []
        };

const jobs_viewset = new ViewSet('jobs', '/home/jobs/', job);
const codebase_viewset = new ViewSet('codebases', '/library/code/', codebase);

export default new Vuex.Store({
    modules: { jobs: jobs_viewset.module, codebases: codebase_viewset.module }
});

export const api = {
    job: jobs_viewset.api,
    codebase: codebase_viewset.api
};