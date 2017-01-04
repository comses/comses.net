import {ActionContext} from 'vuex'

import * as api from '../api/index'
// import router from '../router-config'
import {State, PageQuery} from './types'
import * as types from './types'


export default {
    retrieveJobs({commit}: ActionContext<State, State>, pq: PageQuery) {
        api.retrieveJobs(job_list => {
            commit(types.RECIEVE_ALL,
                job_list)
        }, pq);
    },

    retrieveJob(store: ActionContext<State, State>, job_id: number) {
        return api.retrieveJob(job => {
            store.commit(types.RETRIEVE_JOB_BY_ID, job)
        }, job_id)
    },

    retrieveOrGetJob({dispatch, commit, state}: ActionContext<State, State>, job_id: number) {
        for (let ind = 0; ind < state.job.list.results.length; ind++) {
            let job = state.job.list.results[ind];
            if (job.id === job_id) {
                console.log({ind});
                commit(types.GET_JOB_FROM_JOB_LIST_BY_IND, ind);
                return;
            }
        }

        dispatch('retrieveJob', job_id);
    }
}