import {AxiosRequestConfig, AxiosResponse} from 'axios'
import * as queryString from 'query-string'
import {api} from 'connection'
import {CreateOrUpdateHandler} from "@/api/handler"
import {pickBy, isEmpty} from 'lodash'

abstract class BaseAPI {

    abstract baseUrl();

    detailUrl(id: string | number) {
        return `${this.baseUrl()}${id}/`;
    }
    createUrl() {
        return this.baseUrl();
    }
    delete(id: string | number) {
        return api.delete(this.detailUrl(id));
    }
    retrieve(id: string | number) {
        return api.get(this.detailUrl(id));
    }
    update(id: string | number, handler: CreateOrUpdateHandler) {
        return api.put(this.detailUrl(id), handler);
    }
    create(handler: CreateOrUpdateHandler) {
        return api.post(this.createUrl(), handler);
    }
    searchUrl(queryObject) {
        let filteredObject = pickBy(queryObject);
        const qs = queryString.stringify(filteredObject);
        if (isEmpty(qs)) {
            return this.baseUrl();
        }
        return `${this.baseUrl()}?${qs}`
    }

}

export class EventAPI extends BaseAPI {
    baseUrl() {
        return '/events/';
    }
}

export class JobAPI extends BaseAPI {
    baseUrl() {
        return '/jobs/';
    }
}

export class ReviewEditorAPI {
    baseUrl() {
        return '/reviews/'
    }

    listInvitationsUrl(review_uuid) {
        return `${this.baseUrl()}${review_uuid}/editor/invitations/`;
    }

    listInvitations(review_uuid) {
        return api.get(this.listInvitationsUrl(review_uuid));
    }

    listFeedbackUrl(review_uuid) {
        return `${this.baseUrl()}${review_uuid}/editor/feedback/`;
    }

    listFeedback(review_uuid) {
        return api.get(this.listFeedbackUrl(review_uuid));
    }

    findReviewersUrl({query}) {
        return `/reviewers/?query=${query}`
    }

    findReviewers({query}) {
        return api.axios.get(this.findReviewersUrl({query}));
    }

    sendInvitationUrl({review_uuid}) {
        return `${this.baseUrl()}${review_uuid}/editor/invitations/send_invitation/`
    }

    sendInvitation({review_uuid}, candidate_reviewer) {
        return api.axios.post(this.sendInvitationUrl({review_uuid}), candidate_reviewer);
    }

    resendInvitationUrl({slug, invitation_slug}) {
        return `${this.baseUrl()}${slug}/editor/invitations/${invitation_slug}/resend_invitation/`
    }

    resendInvitation({slug, invitation_slug}) {
        return api.axios.post(this.resendInvitationUrl({slug, invitation_slug}));
    }

    reviewUrl({slug}) {
        return `${this.baseUrl()}${slug}/editor/`;
    }

    changeStatus({slug}, status) {
        return api.axios.put(this.reviewUrl({slug}), {status});
    }
 }

export class ProfileAPI extends BaseAPI {

    baseUrl() {
        return '/users/';
    }

    listUrl(q: { query?: string, page: number }) {
        const qs = queryString.stringify(q);
        return `${this.baseUrl()}${qs ? `?${qs}` : ''}`;
    }

    uploadPictureUrl(pk: number) {
        return `${this.detailUrl(pk)}upload_picture/`
    }

    list(q: { query?: string, page: number }) {
        return api.get(this.listUrl(q));
    }

    search(q: {query?: string, page: number}) {
        return api.get(this.searchUrl(q));
    }

    uploadProfilePicture({pk}, file) {
        const formData = new FormData();
        formData.append('file', file);
        return api.postForm(this.uploadPictureUrl(pk), formData,
            {headers: {'Content-Type': 'multipart/form-data'}})
    }

}

export class CodebaseAPI extends BaseAPI {
    baseUrl() {
        return '/codebases/';
    }

    delete(id: string | number) {
        return api.delete(`/test_codebases/${id}/`);
    }

    mediaListUrl(identifier) {
        return `${this.baseUrl()}${identifier}/media/`;
    }

    mediaList(identifier) {
        return api.get(this.mediaListUrl(identifier));
    }

    mediaDetailUrl(identifier, image_id) {
        return `${this.baseUrl()}${identifier}/media/${image_id}`;
    }

    mediaDelete(identifier, image_id) {
        return api.delete(this.mediaDetailUrl(identifier, image_id));
    }

    mediaClear(identifier) {
        return api.delete(`${this.mediaListUrl(identifier)}clear/`);
    }
}

export class CodebaseReleaseAPI {

    baseUrl() {
        return "/codebases/";
    }

    editUrl({identifier, version_number}) {
        return `${this.detailUrl({identifier, version_number})}edit/`;
    }

    detailUrl({identifier, version_number}) {
        return `${this.baseUrl()}${identifier}/releases/${version_number}/`;
    }

    detailEditUrl({identifier, version_number}) {
        return `${this.detailUrl({identifier, version_number})}?edit`
    }

    clearCategoryUrl({identifier, version_number, category}) {
        return `${this.listOriginalsFileUrl({identifier, version_number, category})}clear_category/`
    }

    listOriginalsFileUrl({identifier, version_number, category}) {
        return `${this.detailUrl({identifier, version_number})}files/originals/${category}/`;
    }

    downloadPreviewUrl({identifier, version_number}) {
        return `${this.detailUrl({identifier, version_number})}download_preview/`;
    }

    updateContributorUrl({identifier, version_number}) {
        return `${this.detailUrl({identifier, version_number})}contributors/`;
    }

    publish({identifier, version_number}, publish_component) {
        return api.post(`${this.detailUrl({identifier, version_number})}publish/`, publish_component);
    }

    notifyReviewersOfChanges({identifier, version_number}, component) {
        return api.post(`${this.detailUrl({identifier, version_number})}notify_reviewers_of_changes/`, component);
    }

    retrieve({identifier, version_number}) {
        return api.get(this.detailEditUrl({identifier, version_number}));
    }

    listOriginalFiles({identifier, version_number, category}) {
        return api.get(this.listOriginalsFileUrl({identifier, version_number, category}));
    }

    downloadPreview({identifier, version_number}) {
        return api.get(this.downloadPreviewUrl({identifier, version_number}));
    }

    uploadFile({identifier, version_number, category}, file, onUploadProgress) {
        const formData = new FormData();
        formData.append('file', file);
        return api.postForm(this.listOriginalsFileUrl({identifier, version_number, category}),
            formData, {headers: {'Content-Type': 'multipart/form-data'}, onUploadProgress});
    }

    deleteFile({path}) {
        return api.delete(path);
    }

    clearCategory({identifier, version_number, category}) {
        return api.delete(this.clearCategoryUrl({identifier, version_number, category}))
    }

    updateDetail({identifier, version_number}, detail) {
        return api.put(
            this.detailEditUrl({identifier, version_number}), detail)
    }

    updateContributors({identifier, version_number}, contributors) {
        return api.put(this.updateContributorUrl({identifier, version_number}), contributors)
    }
}

interface TagQueryParameters {
    query: string;
    type: string;
    page: number;
}

export class TagAPI {

    static listUrl(params: TagQueryParameters) {
        return `/tags/?${queryString.stringify(params)}`;
    }

    static list({query, type="", page = 1}) {
        return api.get(TagAPI.listUrl({query, type, page}));
    }

    static listEventTags({query, page=1}) {
        return TagAPI.list({query, type: "Event", page});
    }

    static listJobTags({query, page=1}) {
        return TagAPI.list({query, type: "Job", page});
    }

    static listCodebaseTags({query, page=1}) {
        return TagAPI.list({query, type: "Codebase", page});
    }

    static listProfileTags({query, page=1}) {
        return TagAPI.list({query, type: "Profile", page});
    }

}

export class ContributorAPI {

    static listUrl(filters: { query?: string, page: number }) {
        return `/contributors/?${queryString.stringify(filters)}`
    }

    static list({query, page = 1}) {
        return api.get(ContributorAPI.listUrl({query, page}));
    }
}
