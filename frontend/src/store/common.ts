import {Module, ActionContext} from 'vuex'
import { api as axios } from '../api/index'
import * as queryString from 'query-string'

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
}

export interface Codebase extends NullWithId {
    title: string
    description: string

    live: boolean
    is_replication: boolean
    doi: string | null

    keywords: Array<string>
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

interface ViewSetMutations<T> {
    setDetail(state: State<T>, detail: T): void
    setModify(state: State<T>, modify: T): void
    setList(state: State<T>, list: Page<T>): void
    setSearch(state: State<T>, search: string): void
}

interface ViewSetActions<T> {
    fetchDetail(context: ActionContext<State<T>, any>, id: number): any
    fetchModify(context: ActionContext<State<T>, any>, id: number): any
    fetchList(context: ActionContext<State<T>, any>, list: Page<T>): any
    modify(context: ActionContext<State<T>, any>, record): any
}

export interface Payload<T> {
    type: string
    data: T
}

export class ViewSet<T> {
    module: Module<State<T>, any>;
    api: Api;

    constructor(public name: string, base_url: string, state_t: T) {
        /**
         * @param name: Name must match name of module
         * */

        const mutations = this.mutations;
        const actions = this.createActions(base_url);
        const getters = this.createGetters();
        const state = {
            detail: state_t,
            modify: state_t,
            list: defaultPage,
            search: ''
        };

        const api = {
            mutations: this.createMutationApi(mutations),
            actions: this.createActionApi(actions)
        };

        this.module = {
            namespaced: true,
            getters,
            mutations,
            actions,
            state
        };
        this.api = api;
    }

    private mutations = {
        setDetail(state: State<T>, payload: Payload<T>): void {
            state.detail = payload.data;
        },

        setModify(state: State<T>, payload: Payload<T>): void {
            state.modify = payload.data;
        },

        setList(state: State<T>, payload: Payload<Page<T>>): void {
            console.log(state);
            console.log(payload);
            state.list = payload.data;
        },

        setSearch(state: State<T>, payload: Payload<string>): void {
            state.search = payload.data;
        }
    };

    createActions(base_url: string) {

        const fetch = (name: keyof State<T>, mutationName: string) =>
            ({commit}: ActionContext<State<T>, any>, payload: Payload<number>) => {
            return axios.get(base_url + payload.data).then(response =>
                commit({ type: mutationName, data: response.data}));
        };

        const fetchList = ({commit}: ActionContext<State<T>, any>, payload: Payload<PageQuery>) => {
            console.log(payload);
            return axios.get(base_url + '?' + queryString.stringify(payload.data)).then(response =>
                commit({ type: 'setList', data: response.data}))
        };

        const modify = <T extends NullWithId>({commit}: ActionContext<State<T>, any>, payload: Payload<T>) => {
            if (payload.data.id === undefined) {
                return axios.post(base_url, payload.data);
            } else {
                return axios.put(base_url + payload.data.id, modify);
            }
        };

        return {
            fetchDetail: fetch('detail', 'setDetail'),
            fetchModify: fetch('modify', 'setModify'),
            fetchList,
            modify
        }
    }

    // modify -> draft
    createGetters() {
        return {
            detail: (state: State<T>) => state.detail,
            list: (state: State<T>) => state.list,
            modify: (state: State<T>) => state.modify,
            search: (state: State<T>) => state.search
        }
    }

    createActionApi(actions) {
        return {
            fetchDetail: (id: number): Payload<number> => ({data: id, type: this.name + '/fetchDetail'}),
            fetchModify: (id: number): Payload<number> => ({data: id, type: this.name + '/fetchModify'}),
            fetchList: (page_query: PageQuery): Payload<PageQuery> => ({data: page_query, type: this.name + '/fetchList'}),
            modify: <T>(record: T): Payload<T> => ({data: record, type: this.name + '/modify'})
        }
    }

    createMutationApi(mutations) {
        const set = (type: string) => (record: T): Payload<T> => ({data: record, type});

        return {
            setDetail: set(this.name + '/setDetail'),
            setModify: set(this.name + '/setModify'),
            setList: (list: Page<T>): Payload<Page<T>> => ({data: list, type: this.name + '/setList'}),
            setSearch: (search: string): Payload<string> => ({data: search, type: this.name + '/setSearch'})
        }
    }
}

export const defaultPage = {
    count: 0,
    n_pages: 0,
    page: 0,
    query: '',
    range: [],
    results: []
};