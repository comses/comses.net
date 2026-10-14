# Codebase Review Workflow

Peer review assesses a model release's narrative documentation, code quality,
and reproducibility from the supplied instructions. Reviewers provide feedback
and recommend acceptance or revisions. A review editor decides whether to certify
the release.

A **release** is a particular version of a model and its supporting files. A
**review** is the assessment of that release. Each release has one review at most,
and a model can have only one active review at a time.

An active review is open and incomplete. **Closing** a review stops the review
process. **Completing** a review records the editor's certification decision.
Certification applies to the reviewed release; publication is a separate step.
A completed review cannot be reopened.

## The review process

1. **The author requests review.** The release must include the required metadata,
   code, and documentation. The review editor receives a notification.
2. **The editor invites reviewers.** Reviewers accept or decline their
   invitations. After accepting, they can save draft feedback and submit a
   recommendation.
3. **The editor considers the feedback.** If revisions are needed, the editor
   sends notes to the author. The author updates the release and uses the option
   to notify reviewers of changes so they can assess the revisions.
4. **The editor accepts and certifies the release.** Once satisfied with the
   submission, the editor uses **Accept and certify** on submitted reviewer
   feedback. The author receives a certification email.

The review status shows who needs to act next. The editor can change a pending
status to reflect progress.

| Status | Meaning |
| --- | --- |
| Awaiting reviewer feedback | Reviewers need to respond. The editor may need to assign reviewers or resend invitations. |
| Awaiting editor feedback | The editor needs to consider reviewer feedback. |
| Awaiting author release changes | The editor has requested revisions from the author. |
| Review is complete | The editor has certified the release. |

## Requesting review

For an unpublished release, requesting review uses that release and its existing
version number. For a published release, the system creates an unpublished review
draft with copies of its files and metadata. The published release remains
unchanged. Imported releases that have already been published are not eligible
for a review request.

If the model already has an active review, requesting review again uses that
review. It does not create another review or send another editor
notification. If the chosen unpublished release has a closed review, the request
follows the reopening process below.

## Closing a review

Closing ends an open review without certifying the release. It may be appropriate
when a request was premature or spurious, when an author is not adequately
addressing reviewer concerns, or when other circumstances prevent the review
from continuing. The editor should determine how to handle the case based on the
work already recorded.

The author who requested the review or a review editor can use **Close review**
when no reviewer has submitted feedback and no editorial decision has been
recorded. Closing discards unsubmitted feedback drafts. It retains the release,
reviewer invitations and their responses, and the review history. The history
records who closed the review and how many drafts were discarded.

Reviews with submitted feedback, editor notes, or a request for author revisions
require curatorial handling to close. This also applies when the review history
records an earlier feedback submission or editorial decision. The ordinary close
action preserves this work and directs the user to seek curatorial handling.
Closing must not undo certification; withdrawing a published, peer-reviewed model
also requires curatorial oversight.

While a review is closed, reviewers cannot respond to invitations or update
feedback, and editors cannot send invitations or change the review status.
Closing an already closed review leaves its state and history unchanged.

## Reopening a closed request

The author who requested the review or a review editor can use **Re-open review**.
For an unpublished release, the author can also request review again from the
release page. Both routes require the release to have the metadata, code, and
documentation needed for review.

A closed review can be reopened through these actions only if it has no submitted
feedback or editorial decisions, including any recorded in its history. Otherwise,
manual curation by a maintainer or admin is needed. A completed review cannot be 
reopened, and a closed review cannot be reopened while another review of the same 
model is active.

Reopening uses the same review and release, preserving the version number. It
sets the review to **Awaiting reviewer feedback** and notifies the editor once.
Any remaining unsubmitted feedback drafts are discarded so reviewers begin with
fresh feedback.

Existing reviewer invitations keep their links but return to pending. Reviewers
must accept again before adding feedback. Invitation expiry dates remain the
same: the editor must resend an expired invitation before the reviewer can
respond. Reopening does not email reviewers, so the editor should decide which
invitations to resend or which additional reviewers to invite.

Repeating a reopening request does not reset the review again or send another
editor notification. Authors who are revising a release during an active review
should notify reviewers of their changes through the existing review process.

## Certification and publication

Only **Accept and certify** completes a review. Changing the review status alone
does not certify the release. Certification marks the release and model as peer
reviewed, records the editor's decision in the review history, and emails the
author. The reviewed unpublished release can then proceed to publication.

Certification does not publish the release or assign a DOI. Publication and DOI
assignment follow the release's publication process. Completed reviews retain
their feedback and history for inspection. Their feedback is read-only, and
ordinary review actions cannot change or reverse their certification.
