import {Payload} from "./common";
import { api as axios } from '../api/index'
import {ActionContext} from "vuex";

const module_name = 'resources';

interface Image {
    type: 'image'
    value: number
}

interface Paragraph {
    type: 'paragraph'
    value: string
}

interface Meta {
    detail_url: string
    type: string
}

export interface Resource {
    id: number
    title: string
    date: string
    body: Array<Paragraph | Image>
    meta: Meta,
    parent: {
        id: number
        meta: Meta
    }
}

export const api = {
    mutations: {
        setDetail(detail: Resource) {
            return { type: module_name + '/setDetail', data: detail}
        }
    },
    actions: {
        fetchDetail(id: number) {
            return { type: module_name + '/fetchDetail', data: id}
        }
    }
};

const actions = {
    fetchDetail({commit}: ActionContext<Resource, any>, payload: Payload<number>) {
        return axios.get('/api/v1/pages/' + payload.data + '/?fields=title,date,body').then(response => commit({ type: 'setDetail', data: response.data}));
    }
};

const mutations = {
    setDetail(state: Resource, payload: Payload<Resource>) {
        console.log(state);
        console.log(payload);
        state.body = payload.data.body;
    }
};

const state: Resource = {
    id: -1,
    title: '',
    date: '',
    body: [],
    meta: {
        detail_url: '',
        type: ''
    },
    parent: {
        id: -1,
        meta: {
            detail_url: '',
            type: ''
        }
    }
};

const routes = {
    path: '/resources/'
};

export default {
    namespaced: true,
    state,
    actions,
    mutations
}