---
applyTo: "**/review/**,**/library/models.py"
---

# Peer Review Workflow

> Cross-reference: `comses-overview.mdc` for Codebase/CodebaseRelease context.

The peer review system gates a release's `peer_reviewed` flag. An editor coordinates
reviewers, tracks feedback through a state machine, and ultimately certifies the release.
Every state transition is logged to `PeerReviewEventLog`.

---

## State Machine

```
[submitted]
     |
     v
AWAITING_REVIEWER_FEEDBACK   <--- initial status on PeerReview creation
     |
     | reviewer submits PeerReviewerFeedback (reviewer_completed())
     v
AWAITING_EDITOR_FEEDBACK
     |
     |-- editor calls for revisions (editor_called_for_revisions())
     |        v
     |   AWAITING_AUTHOR_CHANGES
     |        |
     |        | author resubmits (author_resubmitted_changes())
     |        |
     |        +--- back to AWAITING_REVIEWER_FEEDBACK (if active reviewers exist)
     |        +--- back to AWAITING_EDITOR_FEEDBACK   (if no active reviewers)
     |
     |-- editor certifies (set_complete_status())
     v
COMPLETE  (terminal)
```

The `closed` boolean is orthogonal to `status` — a review can be closed at any status
without reaching COMPLETE. Closed reviews are excluded from editor dashboards.
`reopen()` clears `closed=True`; it does not change `status`.

---

## ReviewStatus (TextChoices — `library/models.py:1983`)

| Value | Label | Meaning |
|-------|-------|---------|
| `awaiting_reviewer_feedback` | Awaiting reviewer feedback | No reviewer has given feedback yet |
| `awaiting_editor_feedback` | Awaiting editor feedback | At least one reviewer gave feedback; editor hasn't requested changes |
| `awaiting_author_changes` | Awaiting author release changes | Editor requested revisions; author hasn't responded or resubmission not yet approved |
| `complete` | Review is complete | Terminal — release is certified |

`ReviewStatus.is_pending` — property, True for every status except COMPLETE.
`ReviewStatus.simple_display_message` — returns `"Peer review in process"` or `"Peer reviewed"`.

---

## PeerReviewEvent (TextChoices — `library/models.py:2020`)

All events are written to `PeerReviewEventLog` via `PeerReview.log()`.

| Value | Trigger |
|-------|---------|
| `invitation_sent` | `send_candidate_reviewer_email(resend=False)` |
| `invitation_resent` | `send_candidate_reviewer_email(resend=True)` |
| `invitation_accepted` | `PeerReviewInvitation.accept()` |
| `invitation_declined` | `PeerReviewInvitation.decline()` |
| `reviewer_feedback_submitted` | `PeerReviewerFeedback.reviewer_completed()` |
| `author_resubmitted` | `PeerReview.author_resubmitted_changes()` |
| `review_status_updated` | `PeerReview.editor_change_review_status()` — manual editor override |
| `revisions_requested` | `PeerReviewerFeedback.editor_called_for_revisions()` |
| `release_certified` | `PeerReview.set_complete_status()` |
| `review_closed` | `PeerReview.close()` |
| `review_reopened` | `PeerReview.reopen()` |

---

## PeerReview (model — `library/models.py:2118`)

**Fields**

| Field | Type | Notes |
|-------|------|-------|
| `status` | CharField | Default: `AWAITING_REVIEWER_FEEDBACK` |
| `closed` | BooleanField | Default: False. Orthogonal to status. |
| `codebase_release` | OneToOneField → CodebaseRelease | `on_delete=PROTECT` — cannot delete a release under review |
| `submitter` | FK → MemberProfile | `on_delete=PROTECT` |
| `slug` | UUIDField | Used in all review URLs |

**Key methods**

`set_complete_status(editor)` — @transaction.atomic. The completion cascade:
1. Sets `status = COMPLETE`, saves.
2. Logs `RELEASE_CERTIFIED` event.
3. If `codebase_release.is_under_review`: sets release status to `REVIEW_COMPLETE`.
4. Sets `codebase_release.peer_reviewed = True`, saves.
5. Sets `codebase_release.codebase.peer_reviewed = True`, saves.
6. Calls `send_model_certified_email()` → email to submitter, CC to `REVIEW_EDITOR_EMAIL`.

`editor_change_review_status(editor, status)` — logs `REVIEW_STATUS_UPDATED` then sets
the new status. Use this for manual editor overrides; do not set `status` directly.

`author_resubmitted_changes(changes_made=None)` — logs `AUTHOR_RESUBMITTED`, then calls
`send_author_updated_content_email()` which resets status to:
- `AWAITING_REVIEWER_FEEDBACK` if accepted invitations exist
- `AWAITING_EDITOR_FEEDBACK` if no accepted invitations

`log(message, action, author)` — creates a `PeerReviewEventLog` entry via
`self.event_set.create(...)`. The `action` argument must be a `PeerReviewEvent` member;
it is stored as `.name` (the string key, not the value).

`get_codebase_latest_active_review(codebase)` — classmethod. Returns latest review that
is neither COMPLETE nor closed. Use this before creating a new review to avoid duplicates.

---

## PeerReviewer (model — `library/models.py:2305`)

A separate registry model that wraps `MemberProfile`. A `MemberProfile` must have an
associated `PeerReviewer` record before they can receive invitations.

| Field | Notes |
|-------|-------|
| `member_profile` | OneToOneField, `related_name="peer_reviewer"` |
| `is_active` | BooleanField, default True |
| `programming_languages` | ArrayField of CharField |
| `subject_areas` | ArrayField of CharField |

---

## PeerReviewInvitation (model — `library/models.py:2369`)

Connects an editor, a candidate reviewer, and a review. One invitation per reviewer per
review (`unique_together = (("review", "reviewer"))`).

**Fields**

| Field | Type | Notes |
|-------|------|-------|
| `review` | FK → PeerReview | `related_name="invitation_set"` |
| `editor` | FK → MemberProfile | `on_delete=PROTECT` |
| `candidate_reviewer` | FK → MemberProfile | Legacy field; prefer `reviewer` |
| `reviewer` | FK → PeerReviewer | `on_delete=PROTECT`, nullable |
| `optional_message` | MarkdownField | Appended to invitation email |
| `slug` | UUIDField | Used in invitation URLs |
| `accepted` | BooleanField (nullable) | `None`=pending, `True`=accepted, `False`=declined |

**Invitation lifecycle**

```
editor sends invite
  → send_candidate_reviewer_email()  → logs INVITATION_SENT
  → (optional) resend
  → send_candidate_reviewer_email(resend=True)  → logs INVITATION_RESENT

reviewer accepts
  → accept()  → accepted=True, logs INVITATION_ACCEPTED, sends email to reviewer + CC editor
  → returns PeerReviewerFeedback instance (auto-created via latest_feedback)

reviewer declines
  → decline()  → accepted=False, logs INVITATION_DECLINED, sends email to editor
```

`expiration_date` — `date_sent + settings.PEER_REVIEW_INVITATION_EXPIRATION` (days).
`is_expired` — compares `timezone.now()` against `expiration_date`.

`latest_feedback` property — returns the last `PeerReviewerFeedback` for this invitation,
or creates a blank one if none exist. Creates on read — see gotcha #2 below.

---

## PeerReviewerFeedback (model — `library/models.py:2519`)

One feedback record per review round per reviewer. Multiple records can exist per
invitation (one per resubmission cycle).

**Recommendation choices** (`ReviewerRecommendation` — `library/models.py:1970`)

| Value | Meaning |
|-------|---------|
| `accept` | Model meets CoMSES peer review requirements |
| `revise` | Model must be revised |

**Checklist fields** (all Boolean + companion TextField for comments)

| Boolean | Comments field |
|---------|----------------|
| `has_narrative_documentation` | `narrative_documentation_comments` |
| `has_clean_code` | `clean_code_comments` |
| `is_runnable` | `runnable_comments` |

**Other fields**

| Field | Notes |
|-------|-------|
| `private_reviewer_notes` | MarkdownField — editor-only visibility |
| `private_editor_notes` | MarkdownField — editor-only |
| `notes_to_author` | MarkdownField — editor-compiled summary sent to author |
| `reviewer_submitted` | BooleanField — True when reviewer finalizes; triggers editor notification |

**Key methods**

`reviewer_completed()` — @transaction.atomic:
1. Sets `review.status = AWAITING_EDITOR_FEEDBACK`, saves.
2. Logs `REVIEWER_FEEDBACK_SUBMITTED`.
3. Emails editor (action needed) and reviewer (thank-you/confirmation).

`editor_called_for_revisions(editor)` — @transaction.atomic:
1. Logs `REVISIONS_REQUESTED`.
2. Sets `review.status = AWAITING_AUTHOR_CHANGES`, saves.
3. Emails both `review.submitter` and `codebase_release.submitter` (deduped via set).

---

## PeerReviewEventLog (model — `library/models.py:3101`)

Append-only audit trail. Never modified after creation.

| Field | Type | Notes |
|-------|------|-------|
| `review` | FK → PeerReview | `related_name="event_set"` |
| `action` | CharField | Stores `PeerReviewEvent.name` (the key, e.g. `"INVITATION_SENT"`) |
| `author` | FK → MemberProfile | Actor who triggered the event |
| `message` | CharField(500) | Human-readable description, blank allowed |

Access via `review.event_set.all()` ordered by `date_created`.

---

## Completion Cascade (verified)

```
editor calls set_complete_status(editor)
    └─ review.status = COMPLETE
    └─ PeerReviewEventLog(action=RELEASE_CERTIFIED) created
    └─ if release.is_under_review:
           release.status = REVIEW_COMPLETE
    └─ release.peer_reviewed = True  ← release flag
    └─ release.codebase.peer_reviewed = True  ← codebase flag (propagates up)
    └─ send_model_certified_email()
           → to: submitter.email
           → cc: REVIEW_EDITOR_EMAIL
```

Both the release and its parent codebase are marked peer-reviewed in a single atomic
transaction. If either save fails, neither flag is set and no email is sent.

---

## Gotchas

**Gotcha 1 — `codebase_release` uses PROTECT.**
`CodebaseRelease` cannot be deleted while a `PeerReview` exists for it. Attempting to
delete a release under review raises `ProtectedError`. You must delete the review first
or ensure it is complete.

**Gotcha 2 — `latest_feedback` creates on read.**
`PeerReviewInvitation.latest_feedback` calls `self.feedback_set.create()` when no
feedback exists. Accessing this property in a non-transactional context (e.g., a list
view) silently inserts a blank row. Use `feedback_set.last()` directly if you only want
to read.

**Gotcha 3 — `action` stored as `.name`, not `.value`.**
`PeerReview.log()` stores `action.name` in `PeerReviewEventLog.action`. The field has
`choices=PeerReviewEvent.choices` which uses `.value` strings (e.g., `"invitation_sent"`).
This means stored values are uppercase keys (`"INVITATION_SENT"`), not the lowercase
display values — filtering `event_set` by value string will return nothing. Use the
`.name` attribute or `PeerReviewEvent.INVITATION_SENT.name` when querying.

**Gotcha 4 — Dual submitter emails on revisions.**
`editor_called_for_revisions()` builds recipients as
`{review.submitter.email, codebase_release.submitter.email}`. These are usually the same
person but not always. Both receive the revisions email; the editor receives a BCC copy.
Do not assume `review.submitter == codebase_release.submitter`.

**Gotcha 5 — `closed` does not stop status transitions.**
There is no guard preventing status mutations on a closed review. If you add code that
changes `status`, check `review.is_open` first or the state machine will diverge from
what the dashboard shows.
