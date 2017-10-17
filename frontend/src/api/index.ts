import {AxiosRequestConfig, AxiosResponse} from 'axios'
import * as queryString from 'query-string'
import {api} from 'api/connection'
import {CreateOrUpdateHandler} from "api/handler";

export const eventAPI = {
    baseUrl: '/jobs/',
    detailUrl(id: number) {
        return `/events/${id}/`;
    },
    createUrl() {
        return `/events/`;
    },
    delete(id: number) {
        return api.delete(this.detailUrl(id));
    },
    retrieve(id: number) {
        return api.get(this.detailUrl(id));
    },
    update(id: number, event: CreateOrUpdateHandler) {
        return api.put(this.detailUrl(id), event);
    },
    create(event_component: CreateOrUpdateHandler) {
        return api.post(this.createUrl(), event_component);
    }
};

export const jobAPI = {
    baseUrl: '/jobs/',
    detailUrl(id: number) {
        return `/jobs/${id}/`;
    },
    createUrl() {
        return `/jobs/`;
    },
    retrieve(id: number) {
        return api.get(this.detailUrl(id));
    },
    delete(id: number) {
        return api.delete(this.detailUrl(id));
    },
    update(id: number, job_component: CreateOrUpdateHandler) {
        return api.put(this.detailUrl(id), job_component);
    },
    create(job_component: CreateOrUpdateHandler) {
        return api.post(this.createUrl(), job_component);
    }
};

export const profileAPI = {
    baseUrl: '/users/',
    listUrl(q: { query?: string, page: number }) {
        const qs = queryString.stringify(q);
        return `/users/${qs ? `?${qs}` : ''}`;
    },
    detailUrl(username: string) {
        return `/users/${username}/`;
    },
    uploadPictureUrl(username: string) {
        return `${this.detailUrl(username)}upload_picture/`
    },
    list(q: { query?: string, page: number }) {
        return api.get(this.listUrl(q));
    },
    retrieve(username) {
        return api.get(this.detailUrl(username));
    },
    update(username, profile_component) {
        return api.put(this.detailUrl(username), profile_component);
    },
    uploadProfilePicture({username}, file) {
        const formData = new FormData();
        formData.append('file', file);
        return api.postForm(this.uploadPictureUrl(username), formData,
            {headers: {'Content-Type': 'multipart/form-data'}})
    }
};

export const codebaseAPI = {
    baseUrl: '/codebases/',
    listUrl() {
        return this.baseUrl;
    },
    detailUrl(identifier) {
        return `/codebases/${identifier}/`;
    },
    create(codebase) {
        return api.post(this.listUrl(), codebase);
    },
    delete(identifier) {
        return api.delete(this.detailUrl(identifier));
    },
    update(identifier, codebase_component: CreateOrUpdateHandler) {
        return api.put(this.detailUrl(identifier), codebase_component);
    },
    retrieve(identifier) {
        return api.get(this.detailUrl(identifier));
    }
};

export const codebaseReleaseAPI = {
    baseUrl: '/codebases/',
    detailUrl({identifier, version_number}) {
        return `/codebases/${identifier}/releases/${version_number}/`;
    },
    listFileUrl({identifier, version_number, upload_type}) {
        return `${this.detailUrl({identifier, version_number})}files/${upload_type}/`;
    },
    updateContributorUrl({identifier, version_number}) {
        return `${this.detailUrl({identifier, version_number})}contributors/`;
    },
    publish({identifier, version_number}, publish_component) {
        return api.post(`${this.detailUrl({identifier, version_number})}publish/`, publish_component);
    },
    retrieve({identifier, version_number}) {
        return api.get(this.detailUrl({identifier, version_number}));
    },
    listFiles({identifier, version_number, upload_type}) {
        return api.get(this.listFileUrl({identifier, version_number, upload_type}));
    },
    uploadFile({path}, file, onUploadProgress) {
        const formData = new FormData();
        formData.append('file', file);
        return api.postForm(path, formData, {headers: {'Content-Type': 'multipart/form-data'}, onUploadProgress});
    },
    deleteFile({path}) {
        return api.delete(path);
    },
    updateDetail({identifier, version_number}, detail) {
        return api.put(
            this.detailUrl({identifier, version_number}), detail)
    },
    updateContributors({identifier, version_number}, contributors) {
        return api.put(this.updateContributorUrl({identifier, version_number}), contributors)
    }
};

export const tagAPI = {
    listUrl({query, page}) {
        let filters: object = {page};
        if (query) {
            filters['query'] = query;
        }
        return `/tags/?${queryString.stringify(filters)}`;
    },
    list({query, page = 1}) {
        return api.get(this.listUrl({query, page}));
    }
};

export const contributorAPI = {
    listUrl(filters: { query?: string, page: number }) {
        return `/contributors/?${queryString.stringify(filters)}`
    },
    list({query, page = 1}) {
        return api.get(this.listUrl({query, page}));
    }
};