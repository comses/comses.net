import * as Vue from 'vue'
import * as Router from 'vue-router'

import { PageQuery } from './store/types'
import store from './store/index'
import actions from './store/actions'

import JobDetail from './components/JobDetail.vue'
import JobList from './components/JobList'

Vue.use(Router);

const routes = {
    JOB_LIST: 'job_list',
    JOB_DETAIL: 'job_detail'
};

const router = new Router({
    routes: [
        {
            path: '/jobs/',
            name: routes.JOB_LIST,
            component: JobList
        },
        {
            path: '/home/jobs/:jobId/',
            name: routes.JOB_DETAIL,
            component: JobDetail
        }
    ]
});

router.beforeEach((to, from, next) => {
   switch (to.name) {
       case routes.JOB_LIST: {
           store.dispatch('retrieveJobs', to.query);
           break;
       }
       case routes.JOB_DETAIL: {
           store.dispatch('retrieveJob', parseInt(to.params['jobId']));
           break;
       }
   }
   next();
});



export default router;