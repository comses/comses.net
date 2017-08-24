import axios from 'axios'
import {AxiosResponse} from "axios";
import * as _ from 'lodash'
import * as queryString from 'query-string'
import {api_base} from "api/connection"

export const eventAPI = {
    detailUrl(id) {
        return `${__BASE_URL__}/events/${id}/`;
    },
    createUrl() {
        return `${__BASE_URL__}/events/`;
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
        return `${__BASE_URL__}/jobs/${id}/`;
    },
    createUrl() {
        return `${__BASE_URL__}/jobs/`;
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
    detailUrl(username: string) {
        return `${__BASE_URL__}/users/${username}/`;
    },
    retrieve(username) {
        return api_base.get(this.detailUrl(username));
    },
    create(profile) {
        return api_base.post(this.detailUrl(profile.username), profile);
    },
    update(profile) {
        return api_base.put(this.detailUrl(profile.username), profile);
    }
};

export const codebaseAPI = {
    createUrl(identifier) {
        return `${__BASE_URL__}/codebases/${identifier}/`;
    },
    create(identifier) {
        return api_base.post(this.createUrl(identifier));
    }
};

export const codebaseReleaseAPI = {
    detailUrl({identifier, version_number}) {
        return `${__BASE_URL__}/codebases/${identifier}/releases/${version_number}/`;
    },
    updateContributorUrl({identifier, version_number}) {
        return `${this.detailUrl(identifier, version_number)}contributors/`;
    },
    retrieve({identifier, version_number}) {
        return api_base.get(this.detailUrl({identifier, version_number}));
    },
    updateDetail({identifier, version_number}, detail) {
        return api_base.put(
            this.detailUrl(identifier, version_number), detail)
    },
    updateContributors({identifier, version_number}, contributors) {
        return api_base.put(this.updateContributorUrl(), contributors)
    }
};

export const tagAPI = {
    listUrl({query, page}) {
        let filters: object = {page};
        if (query) {
            filters['query'] = query;
        }
        return `${__BASE_URL__}/tags/?${queryString.stringify(filters)}`;
    },
    list({ query, page = 1}) {
        return api_base.get(this.listUrl({query, page}));
    }
};

export const contributorAPI = {
    listUrl({query, page}) {
        let filters: object = {page};
        if (query) {
            filters['query'] = query
        }
        return `${__BASE_URL__}/contributors/?${queryString.stringify(filters)}`
    },
    list({query, page=1}) {
        return api_base.get(this.listUrl({query,page}));
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