import {ActionContext} from 'vuex'

import * as api from '../api/index'
import {State, PageQuery, TransientJob} from './types'
import { MutationAPI } from './mutations'

export namespace ActionNames {
    export type CREATE_JOB = 'CREATE_JOB';
    export const CREATE_JOB: CREATE_JOB = 'CREATE_JOB';

    export type FETCH_JOB = 'FETCH_JOB';
    export const FETCH_JOB: FETCH_JOB = 'FETCH_JOB';

    export type FETCH_OR_SET_JOB = 'FETCH_OR_GET_JOB';
    export const FETCH_OR_SET_JOB: FETCH_OR_SET_JOB = 'FETCH_OR_GET_JOB';

    export type FETCH_JOB_PAGE = 'FETCH_JOB_PAGE';
    export const FETCH_JOB_PAGE: FETCH_JOB_PAGE = 'FETCH_JOB_PAGE';
}

interface CreateJob {
    type: ActionNames.CREATE_JOB
    transient_job: TransientJob
}

interface FetchJobPage {
    type: ActionNames.FETCH_JOB_PAGE
    page_query: PageQuery
}

interface FetchJob {
    type: ActionNames.FETCH_JOB
    id: number
}

interface FetchOrSetJob {
    type: ActionNames.FETCH_OR_SET_JOB
    id: number
}

type Actions = CreateJob | FetchJob | FetchOrSetJob | FetchJobPage

export const ActionAPI = {
    createJob: (transient_job: TransientJob): CreateJob => ({ type: ActionNames.CREATE_JOB, transient_job }),
    fetchJobPage: (page_query: PageQuery) => ({ type: ActionNames.FETCH_JOB_PAGE, page_query }),
    fetchJob: (id: number): FetchJob => ({type: ActionNames.FETCH_JOB, id}),
    fetchOrSetJob: (id: number): FetchOrSetJob => ({type: ActionNames.FETCH_OR_SET_JOB, id})
};

export const actions = {
    [ActionNames.CREATE_JOB]({commit}: ActionContext<State, State>, new_job: TransientJob) {
        return api.createJob(job => {
            console.log(job)
        }, new_job);
    },

    [ActionNames.FETCH_JOB_PAGE]({commit}: ActionContext<State, State>, pq: PageQuery) {
        return api.retrieveJobs(job_list => {
            commit(MutationAPI.setJobPage(job_list))
        }, pq);
    },

    [ActionNames.FETCH_JOB](store: ActionContext<State, State>, job_id: number) {
        return api.retrieveJob(job => {
            store.commit(MutationAPI.setJob(job))
        }, job_id)
    },

    [ActionNames.FETCH_OR_SET_JOB]({dispatch, commit, state}: ActionContext<State, State>, job_id: number) {
        for (let ind = 0; ind < state.job.page.results.length; ind++) {
            let job = state.job.page.results[ind];
            if (job.id === job_id) {
                console.log({ind});
                commit(MutationAPI.setJobByInd(ind));
                return;
            }
        }

        dispatch(ActionAPI.fetchJob(job_id));
    }
};


// type ActionNames = 'a' | 'b';
// type ActionName<T extends ActionNames> = { [K in ActionNames]: T }[T]
// const c: ActionName<'c'> = 'c';

