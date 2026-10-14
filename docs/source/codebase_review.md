# Codebase Review Workflow

Peer review certifies a specific model release against three software integrity
criteria: narrative documentation, code quality, and reproducibility from the
provided instructions. Reviewers recommend acceptance or revisions; an editor
makes the certification decision.

## State and invariants

A release has at most one `PeerReview`. A codebase has at most one active review
through the supported request and reopen workflows. An active review is neither
closed nor complete. Closure and completion are separate states: closing cancels
a premature request; completion records certification and cannot be reversed by
ordinary review actions.

| Review status | Meaning |
| --- | --- |
| `awaiting_reviewer_feedback` | Review requested or restarted; reviewers need to respond. The editor may still need to assign or resend invitations. |
| `awaiting_editor_feedback` | Reviewer feedback needs editorial attention. |
| `awaiting_author_changes` | The editor has requested revisions to the release. |
| `complete` | The editor has explicitly certified the release. |

Release status and review status are distinct. An unpublished release undergoing
review has release status `under_review`; certification changes it to
`review_complete`. Publication is a separate action. Existing published releases
are preserved when requesting a review: the request creates a new unpublished
review draft with copied files and metadata.

## Requesting, closing, and restarting

| Action and current state | Result |
| --- | --- |
| Request while any active review exists for the codebase | Return that review and its release. Do not create anything or send another notification. |
| Request for an eligible unpublished release without a review | Reuse the release, mark it `under_review`, create its review, and notify the editor. |
| Request for an eligible published release | Create a separate review draft and review, and notify the editor. Imported published releases remain ineligible. |
| Close a premature review | Discard unsubmitted feedback drafts, set `closed=True`, and record a cancellation event; retain the release, invitations, and review history. |
| Close a review with submitted feedback or an editorial decision | Reject and require curatorial handling; preserve all feedback. |
| Close an already closed review | No state change or additional event. |
| Request again for an unpublished release with a closed, incomplete review | Restart the existing review on the same release, with the same version number. |
| Use the direct Re-open review button on an unpublished release | Apply the same restart rules and send the same single editor notification. |
| Reopen an already open review eligible for cancellation | No state change, reset, event, or notification. |
| Attempt to reopen a completed review | Reject, even if the release status is inconsistent with the review status. |
| Attempt direct reopening while another review is active | Reject; do not create a second active review. |

An imported published release cannot request review. A `review_complete` release
cannot be restarted. A release marked `under_review` without a corresponding
closed review is inconsistent and is rejected instead of silently creating a
replacement. Completed reviews attached to an unpublished release are not reused,
regardless of whether they are open or closed.

### Cancelling a premature request

Closing is for the atypical case in which an author requested review before the
release was ready. It is not a general way to discard a review that has progressed.
The close action rejects reviews with any submitted feedback, editor notes or
notes to the author, an author-changes-requested status, or recorded submission,
revisions-requested, or certification events. Completed releases and reviews are
also protected. These cases require curatorial handling, even if an earlier
version of the application already closed the review.

For a premature request, closing deletes only unsubmitted feedback drafts and
records how many were discarded. It preserves the release, invitation UUIDs,
invitation responses, and the review event history. There is no schema change,
archival flag, or new review round. Deleted draft URLs return 404; stale forms
cannot recreate deleted feedback. Reading an invitation summary does not create
new feedback while a review is closed.

### Reopening a cancelled request

Both reopening entry points require the release's metadata and required code and
documentation files to pass the same readiness checks as a new review request.
An incomplete submission remains closed until the author supplies that content.

Reopening reuses the existing release, version number, and review:

- Mark an unpublished release `under_review` and set review status to
  `awaiting_reviewer_feedback`.
- Reset existing invitation responses to pending, keeping reviewer identities and
  UUID links. Reviewers must accept again before saving or submitting feedback.
- Keep invitation send times and expiry dates unchanged. Expired invitations must
  be resent by an editor; reopening does not silently renew them or email reviewers.
- Create fresh blank feedback when needed, including when a reviewer accepts an
  invitation. Reopening itself does not allocate feedback records. Drafts retained
  by an older close action are discarded after the same cancellation checks.
- Record one reopen event and notify the review editor once.

Repeated or concurrent reopen requests do not reset accepted invitations, delete
fresh drafts, create additional feedback records, or repeat editor notifications.
Repeated acceptance or decline of the same invitation does not repeat its event
or notification, and invitation responses do not alter its send timestamp.

The author can submit revised content within an active review through the existing
notify-reviewers workflow; that is distinct from cancelling and reopening it.

## Certification and ordinary status changes

Only **Accept and certify**, on current submitted reviewer feedback, completes a
review. It records a certification event, sets review status to `complete`, marks
the release and codebase as peer reviewed, changes an under-review release to
`review_complete`, and emails the author. Repeating an already completed
certification does not repeat these effects.

The editor status endpoint accepts only valid status values. Selecting `complete`
is rejected with instructions to use Accept and certify. Ordinary status changes
cannot reopen or demote a completed review, or change a closed review. Selecting
the current pending status is a no-op without another event.

Closed or completed reviews reject new invitations, invitation responses,
reviewer submissions, revision requests, and editorial feedback changes. They
retain their history for inspection. Publication and DOI assignment are separate
from certification and are not triggered by a status selector.

## Access, concurrency, and deployment

The review submitter or a user with `library.change_peerreview` may close or
restart a review. Editorial status, invitation management, feedback listings,
and editorial feedback pages require the editor permission. Reviewer invitation
links remain capability links; feedback IDs must belong to the invitation named
in their URL. Review state and the cancellation safeguards are enforced in the
backend, including on POST requests; hiding a form or button is not a permission
check. Invitation and feedback record APIs are read-only. New invitations use the
guarded send-invitation action; resend URLs must identify the invitation's review.

Request, close, restart, certification, and review mutation workflows use the
same codebase row lock and database transactions. They reload review state after
locking, preventing a stale request from reopening a completed review or
creating a second active review. Cancellation draft deletion and its event commit
together; reopening state changes, invitation resets, and its event also commit
together.

This protocol requires no database migration. No automatic repair of historical
review/release disagreements is performed. Reviews that have progressed and
withdrawal of published peer-reviewed models require curatorial oversight;
ordinary close, status, or reopen actions must not undo certification.
