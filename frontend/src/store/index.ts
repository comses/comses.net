import * as Vue from 'vue'
import * as Vuex from 'vuex'

import { job, codebase } from './defaults'
import { ViewSet } from './common'
import resources, { api as resource_api } from './resource'


Vue.use(Vuex);



const jobs_viewset = new ViewSet('jobs', '/api/wagtail/jobs/', job);
const codebase_viewset = new ViewSet('codebases', '/api/library/code/', codebase);

export default new Vuex.Store({
    modules: { jobs: jobs_viewset.module, codebases: codebase_viewset.module, resources }
});

export const api = {
    job: jobs_viewset.api,
    codebase: codebase_viewset.api,
    resource: resource_api
};