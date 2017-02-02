import * as Vue from 'vue'
import * as Router from 'vue-router'

import store from './store/index'

import JobCreate from './pages/job/create'
import JobDetail from './pages/job/detail.vue'
import JobList from './pages/job/list'
import DraftCode from './pages/codebase/modify'
import {ResourceDetail} from './pages/resources/detail'


import {api} from "./store/index";

Vue.use(Router);

const routes = {
    JOB_CREATE: 'job_create',
    JOB_DETAIL: 'job_detail',
    JOB_LIST: 'job_list',
    JOB_UPDATE: 'job_update',
    CODEBASE_LIST: 'codebase_list',
    EVENT_LIST: 'event_list',
    RESOURCE_LIST: 'resource_list',
    LOGIN: 'login',
    HOME: 'home'
};

const router = new Router({
    mode: 'history',
    routes: [
        {
            path: '/jobs/',
            name: routes.JOB_LIST,
            component: JobList,
            meta: {
                heading: 'Jobs'
            },
        },
        {
            path: '/jobs/create/',
            name: routes.JOB_CREATE,
            component: JobCreate
        },
        {
            path: '/jobs/update/:jobId/',
            name: routes.JOB_UPDATE,
            component: JobCreate
        },
        {
            path: '/jobs/detail/:jobId/',
            name: routes.JOB_DETAIL,
            component: JobDetail,
        },
        {
            path: '/events/',
            name: routes.EVENT_LIST,
            component: JobList,
            meta: {
                heading: 'Events'
            }
        },
        {
            path: '/codebases/',
            name: routes.CODEBASE_LIST,
            component: DraftCode,
            meta: {
                heading: 'Code Bases'
            }
        },
        {
            path: '/resources/',
            name: routes.RESOURCE_LIST,
            component: ResourceDetail,
            meta: {
                heading: 'Resources'
            }
        },
        {
            path: '',
            name: routes.HOME,
            component: ResourceDetail,
            meta: {
                heading: 'A growing collection of resources for model-based science',
                subheading: 'A Model Library, Tutorials and FAQs on Agent Based Modeling'
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
            console.log('detail');
            store.dispatch(api.job.actions.fetchDetail(parseInt(to.params['jobId'])));
            break;
        }
        case routes.RESOURCE_LIST: {
            // TODO: lookup a list instead of a particular hardwired page
            store.dispatch(api.resource.actions.fetchDetail(3));
            break;
        }
        case routes.HOME: {

        }
    }
    next();
});


export default router;