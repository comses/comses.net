export const RECIEVE_ALL = 'RECIEVE_ALL';
export const GET_JOB_FROM_JOB_LIST_BY_IND = 'GET_JOB_FROM_JOB_LIST_BY_IND';
export const RETRIEVE_JOB_BY_ID = 'RETRIEVE_JOB_BY_ID';
export const SET_JOB_QUERY_TEXT = 'SET_JOB_QUERY_TEXT';

export interface User {
    username: string,
    last_name: string,
    first_name: string
}

export interface TransientJob {
    title: string,
    description: string
}

export interface Job extends TransientJob {
    submitter: User,
    date_created: string,
    id: number,
    url: string
}

export interface JobPage {
    count: number,
    n_pages: number,
    page_ind: number,
    query: string,
    range: Array<string>,
    results: Array<Job>
}

export interface Dependency {
    identifier: string,
    name: string,
    version: string,
    os: string,
    url: string
}

export interface CodebaseRelease {
    doi: string | null,
    dependencies: Array<Dependency>
    licence: string,
    description: string,
    documentation: string,
    version_number: string,
    os: string,
    platforms: Array<string>,
    programming_languages: Array<string>,
    codebase: number,
    bagit_url: string,
    git_path: string,
    submitter: User
}

export interface Codebase {
    title: string
    description: string

    live: boolean
    is_replication: boolean
    doi: string | null

    keywords: Array<string>
    contributors: Array<string>

}

export interface User {
    username: string
}

export interface State {
    codebase: Codebase,
    job: {detail: Job, page: JobPage, search: string}
    user: User
}

export interface PageQuery {
    query: string,
    page_ind: number
}