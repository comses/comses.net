import { useAxios } from "@/composables/api";
import { toRefs } from "vue";
import type { RequestOptions } from "@/composables/api";
import type { RelatedMemberProfile, UserSearchQueryParams } from "@/types";

export function useReviewEditorAPI() {
  /**
   * Composable function for making requests to the reviews API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/reviews/";
  const reviewersUrl = "/reviewers/";
  const { state, get, post, put, detailUrl, searchUrl } = useAxios(baseUrl);

  async function listInvitations(reviewUUID: string) {
    return get(detailUrl(reviewUUID, ["editor", "invitations"]));
  }

  async function sendInvitation(reviewUUID: string, candidateReviewer: RelatedMemberProfile) {
    return post(
      detailUrl(reviewUUID, ["editor", "invitations", "send_invitation"]),
      candidateReviewer
    );
  }

  async function resendInvitation(slug: string, invitationSlug: string) {
    return post(detailUrl(slug, ["editor", "invitations", invitationSlug, "resend_invitation"]));
  }

  async function listFeedback(reviewUUID: string) {
    return get(detailUrl(reviewUUID, ["editor", "feedback"]));
  }

  async function listEvents(reviewUUID: string) {
    return get(detailUrl(reviewUUID, ["events"]));
  }

  async function changeStatus(slug: string, status: string) {
    return put(detailUrl(slug, ["editor"]), { status });
  }

  async function findReviewers(params: UserSearchQueryParams) {
    return get(searchUrl(params, "/reviewers/"));
  }

  async function createReviewer(data: any, options?: RequestOptions) {
    return post(reviewersUrl, data, options);
  }

  async function updateReviewer(id: string | number, data: any, options?: RequestOptions) {
    return put(detailUrl(id, [], reviewersUrl), data, options);
  }

  async function retrieveReviewer(id: string | number, options?: RequestOptions) {
    return get(detailUrl(id, [], reviewersUrl), options);
  }

  return {
    ...toRefs(state),
    listInvitations,
    listFeedback,
    listEvents,
    findReviewers,
    sendInvitation,
    resendInvitation,
    changeStatus,
    createReviewer,
    updateReviewer,
    retrieveReviewer,
  };
}
