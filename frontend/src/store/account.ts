import { Account, Payload } from './common'
import {ActionContext} from "vuex";
import axios from 'axios'

const name = 'account';

interface Authenticate {
    username: string
    password: string
}

const api = {
    mutations: {
        setLoggedIn(token: string): Payload<string> {
            return { type: 'setLoggedIn', data: token }
        },
        setLoggedOut(): Payload<void> {
            return { type: 'setLoggedOut', data: undefined}
        }

    },
    actions: {
        login(data: Authenticate): Payload<Authenticate> {
            return { type: 'login', data}
        },
        logout(token: string): Payload<string> {
            return {type: 'logout', data: token}
        }
    }
};

const state: Account = {};

const actions = {
    login({commit}: ActionContext<Account, any>, payload: Payload<Authenticate>) {
        axios.post('/api-token-auth/', payload.data).then(response =>
            window.localStorage.setItem('token', response.data))
    },
    logout() {}
};

const mutations = {
    setLoggedIn() {},
    setLoggedOut() {}
};

const module = {
    state,
    actions,
    mutations
};