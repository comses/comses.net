import { useAxios } from "@/composables/api/axios";
import { toRefs } from "vue";

export function useReviewEditorAPI() {
  /**
   * Composable function for making requests to the reviews API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/reviews/";
  const { state, get, post, put, detailUrl } = useAxios(baseUrl);

  async function listInvitations(reviewUUID: string) {
    return get(detailUrl(reviewUUID, ["editor", "invitations"]));
  }

  async function sendInvitation(reviewUUID: string, candidateReviewer: any) {
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

  async function findReviewers(query: string) {
    return get(`/reviewers/?query=${query}`);
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
  };
}
