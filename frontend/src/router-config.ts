import * as Vue from 'vue'
import * as Router from 'vue-router'

import store from './store/index'

import JobCreate from './components/job/create'
import JobDetail from './components/job/detail.vue'
import JobList from './components/job/list'



import {ActionAPI} from "./store/actions";

Vue.use(Router);

const routes = {
    JOB_CREATE: 'job_create',
    JOB_DETAIL: 'job_detail',
    JOB_LIST: 'job_list',
};

const router = new Router({
    routes: [
        {
            path: '/jobs/',
            name: routes.JOB_LIST,
            component: JobList,
            children: []
        },
        {
            path: '/jobs/create/',
            name: routes.JOB_CREATE,
            component: JobCreate
        },
        {
            path: '/jobs/:jobId/',
            name: routes.JOB_DETAIL,
            component: JobDetail
        },
    ]
});

router.beforeEach((to, from, next) => {
    switch (to.name) {
        case routes.JOB_LIST: {
            store.dispatch(ActionAPI.fetchJobPage(<any>to.query));
            break;
        }
        case routes.JOB_DETAIL: {
            store.dispatch(ActionAPI.fetchOrSetJob(parseInt(to.params['jobId'])));
            break;
        }
    }
    next();
});


export default router;