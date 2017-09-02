import {AxiosResponse} from "axios";
import * as queryString from 'query-string'
import {api_base} from "api/connection"

export const eventAPI = {
    detailUrl(id) {
        return `/events/${id}/`;
    },
    createUrl() {
        return `/events/`;
    },
    delete(id: number) {
        return api_base.delete(this.detailUrl(id));
    },
    retrieve(id: number) {
        return api_base.get(this.detailUrl(id));
    },
    update(event) {
        return api_base.put(this.detailUrl(event.id), event);
    },
    create(event) {
        return api_base.post(this.createUrl(), event);
    }
};

export const jobAPI = {
    detailUrl(id) {
        return `/jobs/${id}/`;
    },
    createUrl() {
        return `/jobs/`;
    },
    retrieve(id) {
        return api_base.get(this.detailUrl(id));
    },
    delete(id) {
        return api_base.delete(this.detailUrl(id));
    },
    update(job) {
        return api_base.put(this.detailUrl(job.id), job);
    },
    create(job) {
        return api_base.post(this.createUrl(), job);
    }
};

export const profileAPI = {
    listUrl(q: {query?: string, page: number}) {
        const qs = queryString.stringify(q);
        return `/users/${qs ? `?${qs}` : ''}`;
    },
    detailUrl(username: string) {
        return `/users/${username}/`;
    },
    uploadPictureUrl(username: string) {
        return `${this.detailUrl(username)}upload_picture/`
    },
    list(q: {query?: string, page: number}) {
        return api_base.get(this.listUrl(q));
    },
    retrieve(username) {
        return api_base.get(this.detailUrl(username));
    },
    create(profile) {
        return api_base.post(this.detailUrl(profile.username), profile);
    },
    update(profile) {
        return api_base.put(this.detailUrl(profile.username), profile);
    },
    uploadProfilePicture({username}, file) {
        const formData = new FormData();
        formData.append('file', file);
        return api_base.post(this.uploadPictureUrl(username), formData, {headers: {'Content-Type': 'multipart/form-data'}})
    }
};

export const codebaseAPI = {
    listUrl() {
        return '/codebases/';
    },
    detailUrl(identifier) {
        return `/codebases/${identifier}/`;
    },
    create(codebase) {
        return api_base.post(this.listUrl(), codebase);
    },
    delete(identifier) {
        return api_base.delete(this.detailUrl(identifier));
    },
    update(codebase) {
        return api_base.put(this.detailUrl(codebase.identifier), codebase);
    },
    retrieve(identifier) {
        return api_base.get(this.detailUrl(identifier));
    }
};

export const codebaseReleaseAPI = {
    detailUrl({identifier, version_number}) {
        return `/codebases/${identifier}/releases/${version_number}/`;
    },
    listFileUrl({identifier, version_number, upload_type}) {
        return `${this.detailUrl({identifier, version_number})}files/${upload_type}/`;
    },
    updateContributorUrl({identifier, version_number}) {
        return `${this.detailUrl({identifier, version_number})}contributors/`;
    },
    retrieve({identifier, version_number}) {
        return api_base.get(this.detailUrl({identifier, version_number}));
    },
    listFiles({identifier, version_number, upload_type}) {
        return api_base.get(this.listFileUrl({identifier, version_number, upload_type}));
    },
    uploadFile({path}, file, onUploadProgress) {
        const formData = new FormData();
        formData.append('file', file);
        return api_base.post(path, formData, {headers: {'Content-Type': 'multipart/form-data'}, onUploadProgress});
    },
    deleteFile({path}) {
        return api_base.delete(path);
    },
    updateDetail({identifier, version_number}, detail) {
        return api_base.put(
            this.detailUrl(identifier, version_number), detail)
    },
    updateContributors({identifier, version_number}, contributors) {
        return api_base.put(this.updateContributorUrl({identifier, version_number}), contributors)
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
        return api_base.get(this.listUrl({query, page}));
    }
};

export const contributorAPI = {
    listUrl(filters: { query?: string, page: number }) {
        return `/contributors/?${queryString.stringify(filters)}`
    },
    list({query, page = 1}) {
        return api_base.get(this.listUrl({query, page}));
    }
};

function isAxiosResponse(response: any): response is AxiosResponse {
    return response !== undefined && (<AxiosResponse>response).status !== undefined;
}

class DrfSuccess {
    constructor(public payload: any) {
        this.kind = 'state';
    }

    kind: 'state';
}

class DrfValidationError {
    constructor(public payload: any) {
        this.kind = 'validation_error';
    }

    kind: 'validation_error';
}

class DrfOtherError {
    constructor(public payload: any) {
        this.kind = 'validation_error';
    }

    kind: 'validation_error';
}

type DrfResponse = DrfSuccess | DrfValidationError | DrfOtherError;