import axios from 'axios'
import * as queryString from 'query-string'
import { JobList, PageQuery } from '../store/types'

export const api = axios.create({
   auth: {
       username: 'calvin',
       password: 'test'
   }
});

export function retrieveJobs(cb: (job_list: JobList) => any, pq: PageQuery): Promise<void> {
    /**
     * @param {string} query - The text searched for
     * @param {number} page_ind - The page of the queryset to look at
     */
    const q = queryString.stringify({ query: pq.query, page: pq.page_ind});
    console.log(q);
    return api.get('/home/jobs/?' + q)
        .then((response) => {
            console.log(response);
            return Promise.resolve(cb(response.data));
        })
        .catch((error) => Promise.reject(error));
}

export function retrieveJob(cb, id) {
    return api.get('/home/jobs/' + id)
        .then((response) => {
            return Promise.resolve(cb(response.data));
        })
        .catch((error) => Promise.reject(error));
}