# library — AGENTS.md

Codebase repository, peer review, DOI minting, BagIt archival. See root `AGENTS.md` for commands, structure, and global conventions.

## Key Files

- `models.py` — `PeerReview`, `PeerReviewInvitation`, `PeerReviewerFeedback`, `PeerReviewEventLog`, `ReviewStatus`, `DataCiteRegistrationLog`
- `fs.py` — `CodebaseReleaseFsApi`, `CodebaseReleaseSipStorage`, `CodebaseReleaseAipStorage`, `ArchiveExtractor`
- `doi.py` — `DataCiteApi` — API client, minting, update, logging
- `metadata.py` — `DataCiteConverter`, `CodeMetaConverter`
- `../curator/models.py` — `TagMigrator`, `TagCleanup`, `CanonicalTag`, `CanonicalTagMapping`

## Conventions

### Peer Review

- Use `PeerReview.get_codebase_latest_active_review(codebase)` before creating a new review to avoid duplicates.
- Use `editor_change_review_status(editor, status)` for status changes — do not set `review.status` directly. Direct assignment skips event logging.
- `closed` is orthogonal to `status` — closed does not mean complete. Check `review.is_open` before changing status.
- `PeerReviewEventLog.action` stores `PeerReviewEvent.name` (e.g., `"INVITATION_SENT"`), not `.value` (e.g., `"invitation_sent"`).
- `latest_feedback` on `PeerReviewInvitation` creates a blank row on read if none exist. Use `feedback_set.last()` in read-only contexts.
- `set_complete_status()` atomically sets both `release.peer_reviewed` and `codebase.peer_reviewed` — do not set them independently.
- `PeerReview.codebase_release` uses `on_delete=PROTECT` — delete the review before the release.

### BagIt Archival

- Never serve release files directly — use `X-Accel-Redirect` header for nginx to stream.
- Uploading a zip/tar/rar expands into `sip/data/<category>/` — second upload to same category is blocked until first is removed.
- `build_sip()` clears SIP first — do not call mid-session without understanding side-effects.
- Use `rebuild(metadata_only=True)` to refresh metadata on published releases — safe for production.
- `originals/` always retains raw uploads — source of truth for rebuilding SIP.

### DataCite DOI

- `DataCiteApi` defaults to `dry_run=True` — pass `dry_run=False` explicitly for real minting.
- Never hardcode DOI prefixes — `settings.DATACITE_PREFIX` differs between environments.
- `mint_pending_dois()` is idempotent — checks `is_valid_doi` before minting.

### Tag Curation

- `get_through_tables()` only finds through-models using Wagtail's `ParentalKey` — standard ForeignKey through models are invisible.
- `TagMigrator.create_new_tags()` saves one-by-one (not `bulk_create`) for unique slug generation.
- Keep new migration logic inside `TagCleanupQuerySet.process()` `@transaction.atomic` boundary.

## Pitfalls

```python
# Peer review status
WRONG: release.peer_reviewed = True; release.save()
RIGHT: review.set_complete_status(editor)  # atomic, sets both flags

WRONG: review.status = ReviewStatus.AWAITING_EDITOR_FEEDBACK; review.save()
RIGHT: review.editor_change_review_status(editor, status)

# Event log queries
WRONG: PeerReviewEventLog.objects.filter(action="invitation_sent")
RIGHT: PeerReviewEventLog.objects.filter(action="INVITATION_SENT")  # .name not .value

# Feedback access
WRONG: invitation.latest_feedback  # in a list view — creates blank row as side effect
RIGHT: invitation.feedback_set.last()  # read-only, no side effects

# File serving
WRONG: open(release.archivepath).read()  # serve file directly
RIGHT: response["X-Accel-Redirect"] = "/library/internal/..."

# DOI minting
WRONG: DataCiteApi()  # defaults to dry_run=True — silently no-ops
RIGHT: DataCiteApi(dry_run=False)  # explicit for real minting
```
