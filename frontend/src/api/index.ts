import * as queryString from "query-string";
import { api } from "@/api/connection";
import { CreateOrUpdateHandler } from "@/api/handler";
import { pickBy, isEmpty } from "lodash";

abstract class BaseAPI {
  public abstract baseUrl();

  public detailUrl(id: string | number) {
    return `${this.baseUrl()}${id}/`;
  }
  public createUrl() {
    return this.baseUrl();
  }
  public delete(id: string | number) {
    return api.delete(this.detailUrl(id));
  }
  public retrieve(id: string | number) {
    return api.get(this.detailUrl(id));
  }
  public update(id: string | number, handler: CreateOrUpdateHandler) {
    return api.put(this.detailUrl(id), handler);
  }
  public create(handler: CreateOrUpdateHandler) {
    return api.post(this.createUrl(), handler);
  }
  public searchUrl(queryObject) {
    const filteredObject = pickBy(queryObject);
    const qs = queryString.stringify(filteredObject);
    if (isEmpty(qs)) {
      return this.baseUrl();
    }
    return `${this.baseUrl()}?${qs}`;
  }
}

export class EventAPI extends BaseAPI {
  public baseUrl() {
    return "/events/";
  }
}

export class JobAPI extends BaseAPI {
  public baseUrl() {
    return "/jobs/";
  }
}

export class ReviewEditorAPI {
  public baseUrl() {
    return "/reviews/";
  }

  public listInvitationsUrl(review_uuid) {
    return `${this.baseUrl()}${review_uuid}/editor/invitations/`;
  }

  public listInvitations(review_uuid) {
    return api.get(this.listInvitationsUrl(review_uuid));
  }

  public listFeedbackUrl(review_uuid) {
    return `${this.baseUrl()}${review_uuid}/editor/feedback/`;
  }

  public listFeedback(review_uuid) {
    return api.get(this.listFeedbackUrl(review_uuid));
  }

  public findReviewersUrl({ query }) {
    return `/reviewers/?query=${query}`;
  }

  public findReviewers({ query }) {
    return api.axios.get(this.findReviewersUrl({ query }));
  }

  public sendInvitationUrl({ review_uuid }) {
    return `${this.baseUrl()}${review_uuid}/editor/invitations/send_invitation/`;
  }

  public sendInvitation({ review_uuid }, candidate_reviewer) {
    return api.axios.post(this.sendInvitationUrl({ review_uuid }), candidate_reviewer);
  }

  public resendInvitationUrl({ slug, invitation_slug }) {
    return `${this.baseUrl()}${slug}/editor/invitations/${invitation_slug}/resend_invitation/`;
  }

  public resendInvitation({ slug, invitation_slug }) {
    return api.axios.post(this.resendInvitationUrl({ slug, invitation_slug }));
  }

  public reviewUrl({ slug }) {
    return `${this.baseUrl()}${slug}/editor/`;
  }

  public changeStatus({ slug }, status) {
    return api.axios.put(this.reviewUrl({ slug }), { status });
  }
}

export class ProfileAPI extends BaseAPI {
  public baseUrl() {
    return "/users/";
  }

  public listUrl(q: { query?: string; page: number }) {
    const qs = queryString.stringify(q);
    return `${this.baseUrl()}${qs ? `?${qs}` : ""}`;
  }

  public uploadPictureUrl(pk: number) {
    return `${this.detailUrl(pk)}upload_picture/`;
  }

  public list(q: { query?: string; page: number }) {
    return api.get(this.listUrl(q));
  }

  public search(q: { query?: string; page: number }) {
    return api.get(this.searchUrl(q));
  }

  public uploadProfilePicture({ pk }, file) {
    const formData = new FormData();
    formData.append("file", file);
    return api.postForm(this.uploadPictureUrl(pk), formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  }
}

export class CodebaseAPI extends BaseAPI {
  public baseUrl() {
    return "/codebases/";
  }

  public delete(id: string | number) {
    return api.delete(`/test_codebases/${id}/`);
  }

  public mediaListUrl(identifier) {
    return `${this.baseUrl()}${identifier}/media/`;
  }

  public mediaList(identifier) {
    return api.get(this.mediaListUrl(identifier));
  }

  public mediaDetailUrl(identifier, image_id) {
    return `${this.baseUrl()}${identifier}/media/${image_id}`;
  }

  public mediaDelete(identifier, image_id) {
    return api.delete(this.mediaDetailUrl(identifier, image_id));
  }

  public mediaClear(identifier) {
    return api.delete(`${this.mediaListUrl(identifier)}clear/`);
  }
}

export class CodebaseReleaseAPI {
  public baseUrl() {
    return "/codebases/";
  }

  public editUrl({ identifier, version_number }) {
    return `${this.detailUrl({ identifier, version_number })}edit/`;
  }

  public detailUrl({ identifier, version_number }) {
    return `${this.baseUrl()}${identifier}/releases/${version_number}/`;
  }

  public detailEditUrl({ identifier, version_number }) {
    return `${this.detailUrl({ identifier, version_number })}?edit`;
  }

  public clearCategoryUrl({ identifier, version_number, category }) {
    return `${this.listOriginalsFileUrl({ identifier, version_number, category })}clear_category/`;
  }

  public listOriginalsFileUrl({ identifier, version_number, category }) {
    return `${this.detailUrl({ identifier, version_number })}files/originals/${category}/`;
  }

  public downloadPreviewUrl({ identifier, version_number }) {
    return `${this.detailUrl({ identifier, version_number })}download_preview/`;
  }

  public updateContributorUrl({ identifier, version_number }) {
    return `${this.detailUrl({ identifier, version_number })}contributors/`;
  }

  public downloadRequestUrl({ identifier, version_number }) {
    return `${this.baseUrl()}${identifier}/releases/${version_number}/request_download/`;
  }

  // FIXME: remove when download URL guarding is implemented
  public downloadUrl({ identifier, version_number }) {
    return `${this.baseUrl()}${identifier}/releases/${version_number}/download/`;
  }

  public publish({ identifier, version_number }, publish_component) {
    return api.post(`${this.detailUrl({ identifier, version_number })}publish/`, publish_component);
  }

  public notifyReviewersOfChanges({ identifier, version_number }, component) {
    return api.post(
      `${this.detailUrl({ identifier, version_number })}notify_reviewers_of_changes/`,
      component
    );
  }

  public retrieve({ identifier, version_number }) {
    return api.get(this.detailEditUrl({ identifier, version_number }));
  }

  public listOriginalFiles({ identifier, version_number, category }) {
    return api.get(this.listOriginalsFileUrl({ identifier, version_number, category }));
  }

  public downloadPreview({ identifier, version_number }) {
    return api.get(this.downloadPreviewUrl({ identifier, version_number }));
  }

  public uploadFile({ identifier, version_number, category }, file, onUploadProgress) {
    const formData = new FormData();
    formData.append("file", file);
    return api.postForm(
      this.listOriginalsFileUrl({ identifier, version_number, category }),
      formData,
      { headers: { "Content-Type": "multipart/form-data" }, onUploadProgress }
    );
  }

  public deleteFile({ path }) {
    return api.delete(path);
  }

  public clearCategory({ identifier, version_number, category }) {
    return api.delete(this.clearCategoryUrl({ identifier, version_number, category }));
  }

  public updateDetail({ identifier, version_number }, detail) {
    return api.put(this.detailEditUrl({ identifier, version_number }), detail);
  }

  public updateContributors({ identifier, version_number }, contributors) {
    return api.put(this.updateContributorUrl({ identifier, version_number }), contributors);
  }

  public requestDownload({ identifier, version_number }, handler: CreateOrUpdateHandler) {
    return api.post(this.downloadRequestUrl({ identifier, version_number }), handler);
  }
}

interface TagQueryParameters {
  query: string;
  type: string;
  page: number;
}

export class TagAPI {
  public static listUrl(params: TagQueryParameters) {
    return `/tags/?${queryString.stringify(params)}`;
  }

  public static list({ query, type = "", page = 1 }) {
    return api.get(TagAPI.listUrl({ query, type, page }));
  }

  public static listEventTags({ query, page = 1 }) {
    return TagAPI.list({ query, type: "Event", page });
  }

  public static listJobTags({ query, page = 1 }) {
    return TagAPI.list({ query, type: "Job", page });
  }

  public static listCodebaseTags({ query, page = 1 }) {
    return TagAPI.list({ query, type: "Codebase", page });
  }

  public static listProfileTags({ query, page = 1 }) {
    return TagAPI.list({ query, type: "Profile", page });
  }
}

export class ContributorAPI {
  public static listUrl(filters: { query?: string; page: number }) {
    return `/contributors/?${queryString.stringify(filters)}`;
  }

  public static list({ query, page = 1 }) {
    return api.get(ContributorAPI.listUrl({ query, page }));
  }
}
