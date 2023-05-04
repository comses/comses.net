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

  async function listInvitations(review_uuid: string) {
    return get(detailUrl(review_uuid, ["editor", "invitations"]));
  }

  async function sendInvitation(review_uuid: string, candidate_reviewer: any) {
    return post(
      detailUrl(review_uuid, ["editor", "invitations", "send_invitation"]),
      candidate_reviewer
    );
  }

  async function resendInvitation(slug: string, invitation_slug: string) {
    return post(detailUrl(slug, ["editor", "invitations", invitation_slug, "resend_invitation"]));
  }

  async function listFeedback(review_uuid: string) {
    return get(detailUrl(review_uuid, ["editor", "feedback"]));
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
    findReviewers,
    sendInvitation,
    resendInvitation,
    changeStatus,
  };
}
