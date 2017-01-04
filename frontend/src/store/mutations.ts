import * as types from './types'
import { State, Job, JobList } from './types'

export default {
    [types.RECIEVE_ALL] (state: State, job_list: JobList) {
        state.job.list = job_list;
    },

    [types.RETRIEVE_JOB_BY_ID] (state: State, job: Job) {
        state.job.detail = job;
    },

    [types.GET_JOB_FROM_JOB_LIST_BY_IND] (state: State, job_ind: number) {
        state.job.detail = state.job.list.results[job_ind];
    },

    [types.SET_JOB_QUERY_TEXT] (state: State, text: string) {
        state.job.search = text;
    }
}