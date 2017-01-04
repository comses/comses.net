export const RECIEVE_ALL = 'RECIEVE_ALL';
export const GET_JOB_FROM_JOB_LIST_BY_IND = 'GET_JOB_FROM_JOB_LIST_BY_IND';
export const RETRIEVE_JOB_BY_ID = 'RETRIEVE_JOB_BY_ID';
export const SET_JOB_QUERY_TEXT = 'SET_JOB_QUERY_TEXT';

export interface Job {
    content: string,
    creator: {username: string},
    date_created: string,
    id: number,
    title: string,
    url: string
}

export interface JobList {
    count: number,
    n_pages: number,
    page_ind: number,
    query: string,
    range: Array<string>,
    results: Array<Job>
}

export interface State {
    job: {detail: Job, list: JobList, search: string}
}

export interface PageQuery {
    query: string,
    page_ind: number
}

export namespace Actions {
    export type RETRIEVE_JOBS = 'RETRIEVE_JOBS';
    export type RETRIEVE_JOB = 'RETRIEVE_JOB';
    export const RETRIEVE_JOBS: RETRIEVE_JOBS = 'RETRIEVE_JOBS';
    export const RETRIEVE_JOB: RETRIEVE_JOB = 'RETRIEVE_JOB';

    export type Action = RETRIEVE_JOBS | RETRIEVE_JOB;

    export type RetrieveJobs = {
        type: RETRIEVE_JOBS,
        payload: PageQuery
    }
}

function f(x: Actions.RETRIEVE_JOBS) {
    console.log(x);
}

// f('RETfghgf');