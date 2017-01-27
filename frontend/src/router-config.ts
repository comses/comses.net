import * as Vue from 'vue'
import * as Router from 'vue-router'

import store from './store/index'

import JobCreate from './components/job/create'
import JobDetail from './components/job/detail.vue'
import JobList from './components/job/list'
import DraftCode from './components/codebase/modify'
import { ResourceDetail } from './components/resources/detail'


import { api } from "./store/index";

Vue.use(Router);

const routes = {
    JOB_CREATE: 'job_create',
    JOB_DETAIL: 'job_detail',
    JOB_LIST: 'job_list',
    CODEBASE_LIST: 'codebase_list',
    EVENT_LIST: 'event_list',
    RESOURCE_LIST: 'resource_list',
    LOGIN: 'login',
    HOME: 'home'
};

const router = new Router({
    routes: [
        {
            path: '/jobs/',
            name: routes.JOB_LIST,
            component: JobList,
            children: [],
            meta: {
                name: 'Jobs'
            }
        },
        {
            path: '/jobs/create/',
            name: routes.JOB_CREATE,
            component: JobCreate
        },
        {
            path: '/jobs/:jobId/',
            name: routes.JOB_DETAIL,
            component: JobDetail,
        },
        {
            path: '/events/',
            name: routes.EVENT_LIST,
            component: JobList,
            meta: {
                name: 'Events'
            }
        },
        {
            path: '/codebases/',
            name: routes.CODEBASE_LIST,
            component: DraftCode,
            meta: {
                name: 'Code Bases'
            }
        },
        {
            path: '/resources/',
            name: routes.RESOURCE_LIST,
            component: ResourceDetail,
            meta: {
                name: 'Resources'
            }
        },
        {
            path: '',
            name: routes.HOME,
            component: ResourceDetail,
            meta: {
                name: 'Home'
            }
        }
        // {
        //     path: '/login/',
        //     name: routes.LOGIN,
        //     component: Login
        // }
    ]
});

router.beforeEach((to, from, next) => {
    switch (to.name) {
        case routes.JOB_LIST: {
            console.log(to.query);
            store.dispatch(api.job.actions.fetchList(<any>to.query));
            break;
        }
        case routes.JOB_DETAIL: {
            store.dispatch(api.job.actions.fetchDetail(parseInt(to.params['jobId'])));
            break;
        }
        case routes.RESOURCE_LIST: {
            store.dispatch(api.resource.actions.fetchDetail(3));
            break;
        }
        case routes.HOME: {

        }
    }
    next();
});


export default router;