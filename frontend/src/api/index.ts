import axios from 'axios'
import * as queryString from 'query-string'
import {
    Page, PageQuery, Codebase, Job, CodebaseRelease
} from '../store/common'

const JOBS = '/home/jobs/';
const CODEBASE = '/library/code/';
const CODEBASE_RELEASE = '/library/code_release/';

export const api = axios.create({
    auth: {
        username: 'calvin',
        password: 'test'
    }
});

export function createJob(cb: (job: Job) => any, new_job: {title: string, description: string}) {
    return api.post(JOBS, new_job)
        .then((response) => {
            return Promise.resolve(cb(response.data));
        })
}

export function retrieveJobs(cb: (job_list: Page<Job>) => any, pq: PageQuery): Promise<void> {
    /**
     * @param {string} query - The text searched for
     * @param {number} page_ind - The page of the queryset to look at
     */
    const q = queryString.stringify(pq);
    return api.get(JOBS + '?' + q)
        .then((response) => {
            console.log(response);
            return Promise.resolve(cb(response.data));
        })
        .catch((error) => Promise.reject(error));
}

export function retrieveJob(cb, id) {
    return api.get(JOBS + id)
        .then((response) => {
            return Promise.resolve(cb(response.data));
        })
        .catch((error) => Promise.reject(error));
}

export const event = {
};

export const job = {
    update(job: Job): Promise<any> {
        return api.put(JOBS + job.id, job);
    },
    create(transient_job: Job) {
        return api.post(JOBS, transient_job);
    },
    list(pq: PageQuery) {
        const q = queryString.stringify(pq);
        return api.get(JOBS + '?' + q);
    },
    detail(id: number) {
        return api.get(JOBS + id);
    }
};

export const codebase = {
    update(codebase: Codebase) {
        return api.put(CODEBASE + codebase.id, codebase);
    },
    create(transient_codebase: Codebase) {
        return api.post(CODEBASE, transient_codebase);
    },
    list(pq: PageQuery) {
        const q = queryString.stringify(pq);
        return api.get(CODEBASE + '?' + q);
    },

    detail(id: number) {
        return api.get(CODEBASE + id);
    }
};


export const codebase_release = {
    update(codebase_release: CodebaseRelease) {
        return api.put(CODEBASE_RELEASE + codebase_release.id, codebase_release);
    },
    create(transient_codebase_release: CodebaseRelease) {
        return api.post(CODEBASE_RELEASE, transient_codebase_release);
    },
    list(pq: PageQuery) {
        const q = queryString.stringify(pq);
        return api.get(CODEBASE_RELEASE + '?' + q);
    },
    detail(id: number) {
        return api.get(CODEBASE_RELEASE + id);
    }
};
