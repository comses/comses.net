import { State, Job, JobPage } from './types'

// don't use this in components, use MutationAPI instead
export const mutations = {
    SET_JOB_PAGE(state: State, job_page: JobPage): void {
        state.job.page = job_page;
    },

    SET_JOB(state: State, job: Job): void {
        state.job.detail = job;
    },

    SET_JOB_BY_IND(state: State, ind: number): void {
        state.job.detail = state.job.page.results[ind];
    },

    SET_JOB_SEARCH(state: State, search: string): void {
        state.job.search = search;
    }
};

interface SetJobPage {
    type: 'SET_JOB_PAGE',
    job_page: JobPage
}

interface SetJob {
    type: 'SET_JOB',
    job: Job
}

interface SetJobByInd {
    type: 'SET_JOB_BY_IND',
    ind: number
}

interface SetJobSearchText {
    type: 'SET_JOB_SEARCH',
    search: string
}

export const MutationAPI = {
    setJobPage: (job_page: JobPage): SetJobPage => ({ type: 'SET_JOB_PAGE', job_page }),
    setJob: (job: Job): SetJob => ({ type: 'SET_JOB', job}),
    setJobByInd: (ind: number): SetJobByInd => ({ type: 'SET_JOB_BY_IND', ind}),
    setJobSearch: (search: string): SetJobSearchText => ({ type: 'SET_JOB_SEARCH', search})
};