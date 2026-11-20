# CoMSES Policies, privacy and contributor guidance

The public collection is intentionally small. One substantive CoMSES Policies page
covers repository scope, credit, licensing, review, preservation, continuity,
conduct and AI, with a clearly marked Terms of Use section. Privacy owns the
data-handling disclosure. Accessibility is a short callout in Policies.
Preparation checklists and license comparisons belong in Education.

| Source | Destination |
| --- | --- |
| `django/home/content/policy.md` | `/about/policy/` (Terms at `#terms-of-use`) |
| `django/home/content/data-privacy.md` | `/about/data-privacy/` |
| `django/home/content/education/content/sharing-models.md` | `/education/sharing-models/` |

The Policies page contains the actual text, not a second index. There are no
managed policy child pages or standalone Terms/accessibility pages. Retired
proposed routes have no aliases or redirects.

## Synchronize content

From the repository root in the intended environment:

```bash
docker compose exec server ./manage.py sync_education_pages
docker compose exec server ./manage.py sync_policy_page
```

Both commands publish first versions by default, including existing initial
drafts that have never been published. This makes the pages available for feedback;
the draft labels remain in the policy text and publication does not adopt a policy.
To keep initial pages unpublished for preview, add `--draft` to either command.

Previously published pages are never automatically republished, even if an editor
has since unpublished them. Later source changes remain pending Wagtail revisions.
An existing live privacy page therefore keeps its published body. A new contributor
guide is published, but changes to an existing education index, including its new
card, still need publication in Wagtail. Neither command changes global navigation.

The policy command reads every source before writing and rolls back on errors,
including incompatible page types or failed publication. Existing page identity,
URL, title and pending edits to other fields are preserved. Source files supersede
CMS-only body edits, with old revisions retained. Initial publication includes
those preserved editorial fields. Rerunning unchanged sources creates no new
revision; a never-published draft can be published using its existing revision.
New pages receive cross-links to Policies, Privacy and Contact.

Unmanaged database pages are not deleted. If an earlier sync created discarded
child pages or a standalone Terms draft, remove those copies manually in Wagtail.
Existing titles and navigation are also preserved; update these manually if an
earlier sync left outdated labels or links. Do not delete or recreate the existing
privacy page. The policy owner is also reconciling a five-year-old database-only
Policies page manually. Its source-code requirement, version-specific DOI rules
and published-file immutability are retained in Policies.

## MarkdownPage callouts

The existing renderer enables Python-Markdown admonitions, tables and heading
anchors. The sanitizer preserves their `div`, `p` and class attributes. Existing
SCSS maps `info` and `prereqs` callouts to Bootstrap alerts and `warning` to the
existing danger style. No renderer, sanitizer or CSS changes are needed.

```markdown
!!! info "Keep ownership and permissions distinct"
    Publishing does not transfer ownership or place a model in the public domain.
```

Use a few callouts for important distinctions, short sections, lists and links to
stable heading anchors. Keep all essential rules in visible text. Do not put the
whole document in callouts or add a second summary that readers must reconcile
with the rules. Keep each Markdown paragraph on one source line: `nl2br` makes
manual paragraph wrapping visible in the rendered page.

## Decisions and operator approvals

The Executive Board approves policies and delegates operational responsibilities.
The documents remain drafts pending adoption; publishing a draft does not itself
adopt it. Finalize the contributor hosting/preservation grant, Terms acceptance,
effective dates and material-change notices through human review. Guidance and
privacy links do not automatically incorporate those documents into the Terms.

| Area | Agreed direction |
| --- | --- |
| Spam screening | Deterministic checks may process private content within CoMSES. AI inference uses only public content and public fields after publication and on public-field changes. |
| Peer-review AI | An unchecked opt-out on the existing review-request workflow covers CoMSES and reviewer assessment/summarization. Disclosed assistance may process private release material with applicable permissions; confidential reviewer correspondence needs separate authorization. Missing historical choices do not authorize AI use. |
| Licensing | OSI-approved licenses for code/scripts by default; separate component licenses and documented exceptions. Delegated curators handle ordinary exceptions; approval criteria still need to be defined. Refusals and exceptional departures can be appealed to the Board. |
| Restricted models | Approved public metadata records may describe restricted files; distinguish metadata rights, actual holdings, access conditions and review limits. |
| Providers | ASU primary, Cloudflare fallback, with separate human approval by provider and use scope. The Board approves documented exceptions; these cannot waive the spam boundary, review opt-out or rights held by others. |
| Local retention | Screening inputs and detailed results become eligible for deletion after three weeks and are removed at the next curator cleanup. This is a target, not a deadline. |
| Moderation | Contact-page intake with email fallback to `support@comses.net`; curator handling, a different curator for reconsideration/conflicts, and Board final internal appeal. Keep outcome records private and explain decisions to requesters. No automatic review of every flag or response deadline is promised. |

Required provider terms, evidence and explicit human approval fields live in
[AI provider terms and operator approval](ai-provider-approval.md). For drafting,
assume ASU inference is private, inputs/outputs are not used for training, and
content retention is limited to inference needs. This is a working assumption,
not verified account terms or operator sign-off. Provider usage metadata has
separate retention rules. Leave operator approval fields for humans to complete.

## SciCodes coverage and remaining approvals

The [SciCodes nine best practices](https://pmc.ncbi.nlm.nih.gov/articles/PMC9455149/)
are coverage topics, not a requirement for nine separate pages. This layout keeps
rules, operational commitments and practical guidance distinguishable.

| Topic | Location and status |
| --- | --- |
| Scope | Policies: Sharing a model; documented exceptions retained. |
| User guidance | Existing FAQ, review instructions and Education; Policies links review and contributor guidance. |
| Contributor guidance | Education: Sharing models, licenses and AI assistance. |
| Authorship | Policies: Credit and licenses; proposed contribution credit and dispute intake. |
| Metadata schema | Policies: Metadata; links the existing technical specification. |
| Conditions of use | Policies: Terms of Use, with contract boundaries explicit. |
| Privacy | Separate privacy page; provider approvals remain human decisions. |
| Retention | Policies: Preservation and withdrawal; separate from screening-evidence cleanup. |
| End of life | Policies: Service continuity; proposed successor search, permissions, identifiers and notice. |

The new authorship, retention and continuity wording remains draft. Before
adoption, confirm the site-wide metadata reuse license and exclusions (no CC0 or
other blanket grant is applied here), ordinary exception criteria and delegation,
withdrawal and citation-record procedures, and continuity resources and transfer
arrangements. The contributor grant and assent decisions above remain open.

The [existing FAQ](https://www.comses.net/about/faq/), checked on 2026-11-18,
already describes long-term preservation and exceptional withdrawal for privacy,
confidentiality or licensing issues. It also describes funds reserved for a
repository transition. Treat that as a public statement to reconcile with the
Board, not independent verification of available funds or successor agreements.
The draft promises no fixed retention term, automatic transfer or named successor.
The technical metadata source is `docs/source/metadata_schema.md`; keep its public
link aligned with the source repository when publishing.

## Zenodo alignment review (2026-11-19)

Reference pages: [unsuitable content](https://support.zenodo.org/help/en-gb/2-content/141-what-content-is-not-suitable-for-zenodo),
[depositor AI guidance](https://support.zenodo.org/help/en-gb/13/227), and
[service AI notice](https://about.zenodo.org/ai-usage-notice/).

The draft adds research-integrity and authorship guidance, keeping documented
simulation outputs and synthetic data in scope. It preserves the policy owner's
recent social/ecological scope wording and consolidates duplicate credit text.
Executable-file discretion applies before publication; published artifacts remain
immutable and concerns follow the withdrawal process.

The policy owner confirmed these CoMSES directions on 2026-11-19:

- Zenodo runs AI at CERN without external cloud APIs. CoMSES plans ASU and a
  separately approved Cloudflare fallback; do not claim local-only processing.
- Its grant-check flags do not automatically block deposits. This is not a
  general statement about all Zenodo spam decisions. CoMSES screening can hide
  listings before human review; do not promise prior review without changing it.
- Zenodo trains classifiers on public metadata. CoMSES requires no-training terms
  from providers, subject to documented Board exceptions. A CoMSES-operated
  metadata-training program would need a separate decision about rights, scope,
  disclosure and permissions; publication alone does not authorize it.

Zenodo also excludes classroom submission batches and most abstract-only records.
No blanket classroom ban is added here; educational models may have research value.
Retain approved metadata-only exceptions for restricted models. Missing AI
disclosure can prompt a correction request; no new automatic-removal rule is added.
No closed list of AI-writing signals is treated as proof of misconduct.

## Content and voice audit (2026-11-19)

Reviewed both managed About sources, the contributor guide and provider approval
requirements against the policy owner's recent edits and the decisions above.
The public drafts needed substantial editing; the internal approval form remains
precise and its unchecked sign-off fields are unchanged.

- Consolidated duplicate credit text and moved the public-access/AI callout into
  the AI section. Preserved the owner's social/ecological scope and short,
  direct instructions.
- Shortened repeated qualifications and operator instructions, particularly in
  Privacy. Preserved the current payload list, disabled-by-default status,
  unverified activation, retention target and distinction between proposed and
  implemented review controls.
- Clarified that executable rejection occurs before publication; published files
  follow withdrawal procedures and cannot be edited in place.
- Removed an unverified blanket claim about analytics IP anonymization. Verify
  the live analytics version/configuration before stating its treatment of IPs.
- Rechecked ASU, Cloudflare, OSI and Creative Commons guidance on 2026-11-19.
  ASU's usage-log period still does not establish content retention or operator
  approval. Its documentation also describes optional external search and image
  fetching; verify whether any selected request path uses those features.
- Retained ASU plus separately approved Cloudflare fallback, pre-review listing
  hiding with reconsideration on request, and no-training terms with documented
  Board exceptions, as confirmed by the policy owner in this session.

No new classroom ban, local-only infrastructure promise, public-metadata training
permission or automatic-removal rule for missing AI disclosure was added. Existing
adoption and implementation decisions remain documented above and below.

## Implementation follow-up

Implementation is deferred from this content change. Keep current capabilities
and proposed requirements distinct:

- The branch's spam implementation defaults to disabled but can screen private
  codebase information and nonpublic account signals. Restrict triggers and
  payloads; recheck visibility before sending queued requests and applying results.
- Persist and enforce per-review AI choices in both review-request entry points,
  the backend and tasks. Define preference changes, pending work and existing
  outputs. No provider exception may override an opt-out.
- Define metadata-only publication, record labels, access controls, review/badge
  limits and identifier handling; the policy content implements none of those features.
- Assign curator cleanup responsibility and cadence. Preserve enough moderation
  state to avoid restoring spam visibility when deleting evidence. Define separate
  retention for logs, backups, exports, evaluation copies and AI review records.
- Assign contact/support monitoring, case assignment, private outcome/correction
  records, notices and Board escalation. Scientific peer review retains its
  dedicated model-detail request workflow.
- Verify enabled settings, deployed field selection, provider paths, fallback,
  additional recipients and logging before describing them as current behavior.

## Privacy provenance and evidence

On 2026-11-09, the privacy body was exported read-only from the local Wagtail
database and compared with the public privacy page. Retrieved text matched the
headings and wording, allowing for rendering differences; its crawl date did not
rule out later production edits. The obsolete security-tool reference was removed
at the policy owner's request. Account-security wording and the description of
stored technical/screening information were deliberate revisions, not evidence of
new production behavior. Compare with the current production revision if needed.

Spam implementation [PR #933](https://github.com/comses/comses.net/pull/933) was
initially inspected at `68b1835e4c7821775ce7c47f4ab7a5438f5ee48e` on 2026-11-09.
By 2026-11-17 it was merged and present on this branch; production activation was
not verified. Payload selection is in `core/models.py` and `library/models.py`;
`core/spam.py` sends content and stores full inputs, model identity, score,
threshold, latency and fallback errors. The workflow can hide content without
prior human review and preserves moderator decisions. Huey failures may reach
Sentry; inspect those paths when confirming recipients and retention.

On 2026-11-17, [ASU documentation](https://docs.rc.asu.edu/ai/api/limits-and-errors/#usage-and-data-handling)
described 180-day gateway usage records excluding prompt and response text.
[Cloudflare Workers AI documentation](https://developers.cloudflare.com/workers-ai/platform/data-usage/)
described no training on customer content and limited standard-inference content
retention, with feature-specific rules and exceptions. Neither establishes the
complete CoMSES account configuration, application logs or local deletion process.

OSI, Creative Commons and W3C accessibility-statement guidance was checked again
on 2026-11-18. Primary licensing guidance and license texts are linked in the
contributor guide. These recommendations change no existing license or DOI.

## Verification

Use disposable services and storage: the standard test target resets its database.

```bash
make test TEST_ARGS='home.tests.test_policy_page home.tests.test_education_content_sync'
```

Tests cover flat page creation, initial publication and `--draft`, draft/live
isolation, identity and pending-edit preservation, no-op reruns, source validation,
transactional rollback, unmanaged
page retention, education synchronization, and rendered internal links/fragments.
The link check includes both About sources, the contributor guide and the
responsible-practices page; it resolves target education pages from their manifest.
Contact, FAQ, People, review, digest and education-index routes are existing site routes
outside this source check. External links are not fetched by the unit tests.

On 2026-11-19, all 30 policy and education tests passed in isolated services using
copied source and synthetic credentials. Coverage includes default initial
publication, `--draft`, earlier initial drafts, unchanged reruns, pages unpublished
by editors, legacy live privacy without publication metadata, rollback,
retained old policy children, and rendered links/callouts. Ruff lint/format and
`git diff --check` passed. No live-site database was modified.

On 2026-11-18, the public metadata-schema source link returned HTTP 200, and the
actual MarkdownPage template was previewed with existing site SCSS at 1280px and
390px. Callouts were readable, with no horizontal overflow or missing contents
anchors. External scripts and web fonts were disabled for that preview. No
renderer, sanitizer or CSS changes were required.
