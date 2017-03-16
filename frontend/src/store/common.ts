import {Module, ActionContext} from 'vuex'
import {api as axios} from '../api/index'
import * as queryString from 'query-string'

export type Errors<T> = {
    [P in keyof T]?: Array<string>
}

export interface NullWithId {
    id?: number
}

export interface PageQuery {
    query: string,
    page: number
}

export interface Page<T> {
    count: number,
    n_pages: number,
    page: number,
    query: string,
    range: Array<string>,
    results: Array<T>
}

export interface User {
    username: string,
    last_name: string,
    first_name: string
}

export interface Account {
    user?: User
    token?: string
}

export interface State<T> {
    detail: T
    modify: T
    list: Page<T>
    search: string
}

export interface Job extends NullWithId {
    submitter?: User
    title: string
    description: string
    summary: string
    tags: Array<string>
}

export interface Codebase extends NullWithId {
    title: string
    description: string

    live: boolean
    is_replication: boolean
    doi: string | null

    keywords: Array<string>

    repository_url: string
    contributors: Array<string>

}

export interface Dependency {
    identifier: string,
    name: string,
    version: string,
    os: string,
    url: string
}

export interface CodebaseRelease extends NullWithId {
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

interface Api {
    mutations: any
    actions: any
}

export interface Payload<T> {
    type: string
    data: T
}

export interface Search {
    query: string
    tags: Array<{ name: string }>
}

export const defaultPage = {
    count: 0,
    n_pages: 0,
    page: 0,
    query: '',
    range: [],
    results: []
};