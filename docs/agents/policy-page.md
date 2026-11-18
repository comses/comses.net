# Policy collection

The canonical index is `django/home/content/policy.md`. The eight proposed policy
bodies live in `django/home/content/policies/`. Privacy is managed by the same
workflow from `django/home/content/data-privacy.md`, but retains its existing
`/about/data-privacy/` URL. Do not create a duplicate privacy page under the index.

## Create and review drafts

In the intended development or staging environment:

```bash
docker compose exec server ./manage.py sync_policy_page
```

The command creates an unpublished `MarkdownPage` index at `/about/policy/` and
child pages for Terms of Use, content submission, acceptable use, review and
publication, copyright and licensing, accessibility, code of conduct, and AI and
automated processing. It also synchronizes the privacy page under About.

All source files are read before writes. The transaction rolls back on a page type
conflict or another failure. Existing pages retain their identity and URL. Bodies
are compared against the latest draft; unchanged sources create no revisions.
Changed bodies create draft revisions, preserving live content and pending edits
to other fields. Titles and other metadata are initial defaults only. If the
previous combined policy draft already exists, change its title to reflect its
new role as an index in Wagtail. Unmanaged children are retained.

The command never publishes, adds links to live pages, or runs automatically at
deployment. Body edits made only in Wagtail are superseded on the next sync, with
old revisions retained. Review and merge source edits before syncing; preview and
publish through Wagtail only after approval. Publish the linked documents before
making the index publicly navigable. A preview of the index does not make its
unpublished child URLs accessible to anonymous visitors.

## Privacy import

On 2026-11-09, the existing privacy body was exported read-only from the local
Wagtail database and compared with the publicly available page at
<https://www.comses.net/about/data-privacy/>. At import, the retrieved public text matched the
section headings and policy wording, allowing for rendered punctuation and
automatically linked URLs. The page title and site-wide cookie notice are outside
the body. Following that comparison, the obsolete security-tool reference was
removed at the policy owner’s request; this is an intentional change from the
production text.

The original Markdown layout is retained because the renderer enables `nl2br`:
rewrapping paragraphs would introduce visible line breaks. The browsing service
reported that its public-page copy was crawled three days earlier, so this check
does not establish that no more recent production edits exist. Compare against
the latest production revision at deployment if that assurance is required.

Privacy is an existing policy, not a newly proposed policy. Do not prepend the
new documents' draft/adoption disclaimer to it. Separately review the accuracy of
analytics and cookie disclosures, data recipients, retention, and security claims
against actual operations. The password-security statement now describes account
protection without specifying algorithms or linking to obsolete framework
documentation. The personal-information section also acknowledges automatically
collected technical information and planned screening records. These are deliberate
revisions to the imported wording, not evidence of new production behavior.

## Spam-processing disclosure

The privacy draft describes planned processing from
[PR #933](https://github.com/comses/comses.net/pull/933), inspected on 2026-11-09 at
head `68b1835e4c7821775ce7c47f4ab7a5438f5ee48e`. The PR was open and unmerged
at that inspection; on 2026-11-17, GitHub reports it merged and the implementation
is present on this branch. This does not establish production activation.
Detection defaults to disabled; the proposed defaults use ASU Research Computing
(`gemma4-31b-it`) with Cloudflare (`clef-omni`) as a fallback. Providers and models
are configurable. Do not describe this as processing confined to the CoMSES web
server or as an already enabled production feature.

`spam_check_content` in `core/models.py`, with field selections in
`library/models.py`, selects submission metadata, profile fields, usernames, signup
timing and linked-account provider
names. It does not include uploaded model files, passwords or dedicated email
fields, but free text can contain personal information. Codebase checks are not
restricted to published records. `core/spam.py` sends the payload to the configured
provider and records the full input, model identity, score, threshold, latency and
fallback error details. This input retention is intended for review and evaluation;
it is not evidence of an approved training or fine-tuning policy.

The PR can hide content automatically. A moderator can overturn a classification,
and subsequent automated checks preserve manual decisions. The disclosure must
not promise prior human review or automatic review of every flag.

Before adoption or activation, confirm the actual deployed configuration, provider
retention and training terms, local input/result retention and deletion rules,
access to moderation evidence, and use in evaluation datasets. Inspect application
and error-reporting logs, including the new Huey/Sentry integration, for additional
recipients or retention. Add confirmed disclosures and align the rollout and
policy effective date. Open weights do not establish confidentiality, a
no-training guarantee, or zero retention. Keep model identifiers in operational
records so the public policy can describe stable purposes and recipients without
becoming stale every time a model changes.

### Publication verification record (2026-11-17)

The branch implementation supports the findings below. The agreed approach is
for human curators to manually support CoMSES retention policies. Production
configuration and execution of that process have not been verified. Keep privacy
and AI disclosures marked as drafts pending human approval. Record evidence and
a verification date before describing assumptions or target behavior as verified. Do not copy secrets or screened user
content into this record.

| Disclosure | Branch evidence | Confirmation needed before publication |
| --- | --- | --- |
| Activation and moderation | `SpamDetectionSettings.enabled` defaults to false. `core/tasks.py` checks that setting before dispatch and execution. A spam classification can hide content without prior human review. | Record the deployed revision and enabled setting. Track public-visibility restrictions as implementation follow-up, including checks before sending queued content and applying results after a visibility change. |
| Screened fields | `ModeratedContent.spam_check_content()` sends selected codebase, job and event text, tags, submission time, username, signup-to-submission timing and linked-account provider names. `MemberProfile.spam_check_content()` sends profile text, affiliations, degrees, industry, tags, username, join time and linked-account provider names. | Compare deployed field selection with the privacy list. Establish whether any separate forum screening exists; this implementation does not establish it. Uploaded files, passwords and dedicated email fields are not selected, but selected text can contain email addresses or other personal information. Avoid an absolute promise that emails are never transmitted. |
| Providers and fallback | `core/spam.py` sends the selected content as `state` alongside model identity and spam instructions. ASU and Cloudflare adapters are configurable; missing credentials can cause a configured provider to be skipped. | Confirm effective provider/model settings, allowed destinations, credential availability and fallback behavior without exposing credentials. Inspect the ASU base URL and the Cloudflare request path for gateways or other intermediaries. |
| Local retention and deletion | `SpamModeration.detection_details` stores full input, score, threshold, latency and fallback errors, with model identity stored separately. Human curators will manually manage retention and deletion. Gate 5 selected eligibility for deletion after three weeks, followed by removal at the next curator cleanup, as a target rather than a deadline. | Record responsible curators, cleanup cadence, deletion steps, scope and evidence of completed deletions. Define whether minimal moderation decisions must remain after evidence is removed; cleanup must not inadvertently restore spam visibility. Establish separate retention rules for logs, exports, evaluation copies, backups and AI review records. Disclose that screening evidence can remain longer than three weeks until cleanup occurs. |
| Provider handling and logs | The provider documentation below was checked on 2026-11-17. Fallback errors are stored locally and logged; Huey errors may reach Sentry. | Recheck applicable provider terms and the deployed logging, caching, proxy and error-reporting paths. Provider documentation alone does not establish application retention. The privacy table's verification date must not imply that local retention or production behavior was verified. |
| Human review | Moderators can overturn classifications, and automated checks preserve manual decisions. Gate 6 selected contact-page intake with email fallback, curator handling, a different curator for prior curator decisions or conflicts, and the Executive Board as final internal appeal authority. Scientific peer review retains its dedicated model-detail request workflow. | Establish monitoring coverage for both moderation intake routes, case assignment, private outcome/correction records, explanations to requesters and Board escalation procedures. Do not imply automatic review of every flag or a guaranteed response time. |

### Provider documentation checked on 2026-11-17

[Cloudflare Workers AI data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/)
states that customer content is not used for model training and standard stateless
inference content is not retained beyond request processing, subject to stated
exceptions. Stateful features, gateway logging/caching, application logs and
operational metadata have separate retention behavior. Check the deployed request
path and applicable terms; do not turn this into an unconditional promise that no
copy of screening data exists.

[ASU API data handling](https://docs.rc.asu.edu/ai/api/limits-and-errors/#usage-and-data-handling)
describes inference on ASU Research Computing hardware and 180-day gateway usage
records that exclude prompt and response text. This does not establish a complete
retention or training policy for every component or feature.

Deployment controls govern payload selection, allowed destinations, fallbacks,
and local storage. Once a hosted API receives a payload, provider-side handling
depends on its controls and service terms. Our application separately retains
screening evidence under PR #933. Public policy should explain purposes,
recipients, retained information and review options; endpoint configuration and
verification evidence belong in operational documentation.

Required provider terms and explicit human approval fields are maintained in
[AI provider terms and operator approval](ai-provider-approval.md). Delegated
operators record the account/service, terms and evidence, permitted data, retention,
recipients and approval. Material departures require a documented Executive Board
exception. For drafting, assume ASU inference is private, submitted inputs and
outputs are not used for training, and content retention is limited to inference
needs. This is a working assumption, separate from usage-metadata retention and
operator sign-off. Approval fields remain pending for human operators to complete.

## AI and licensing content boundaries

The 2026-11-17 revisions separate legal reuse permissions, community expectations,
and service-operated processing. Maintain these responsibilities when editing:

| Document | Owns |
| --- | --- |
| Terms of Use | Contributor hosting grant, relationship to component licenses, assent and incorporation, and the proposed contractual commitment to require no-training provider agreements with approved documented exceptions. |
| AI policy | Practical disclosure of material assistance, community expectations, public-reuse limits and the scope of the proposed provider requirement. |
| Copyright and Licensing | Separate code/data/documentation recommendations, the contributor checklist, accurate open-source labels, ownership and third-party review, and copyright limitations. |
| Content Submission | A short pointer to the license checklist and AI disclosure guidance. |
| Privacy | Screening inputs, recipients, local/provider retention, visibility effects, review requests and explicit operator checks. |

Current primary guidance was checked on 2026-11-17: the
[OSI Open Source Definition](https://opensource.org/osd),
[Creative Commons AI licensing guidance](https://creativecommons.org/cc-license-guidance/)
and [CC FAQ](https://creativecommons.org/faq/), plus the linked MIT, Apache-2.0,
GPL-3.0, CC BY 4.0 and CC0 legal texts in the licensing draft. These recommendations
assign no default license and change no published release or existing grant.

## Agreed policy directions (2026-11-17)

These directions are reflected in the drafts; they do not constitute formal
policy adoption or verification of production behavior.

| Area | Direction |
| --- | --- |
| Authority | The Executive Board approves policies; delegated operators carry out operational responsibilities. |
| Provider terms | Private inference, no training on submitted inputs/outputs, minimal content retention and explicit operator sign-off. The Board approves documented exceptions. ASU privacy is the working assumption recorded above. |
| Spam screening | Deterministic checks may process private content within CoMSES. AI inference uses only publicly visible content and public fields, after publication and on public-field changes. Provider exceptions do not waive this boundary. |
| Peer-review assistance | An unchecked opt-out checkbox on the existing Request Peer Review workflow covers CoMSES-operated AI assessment and summarization, including reviewer use. Disclosed assistance may process private release materials with applicable permissions. Historical requests without a recorded choice do not authorize it. The choice does not authorize training or govern independent third-party reuse. |
| Licensing | OSI-approved licenses are the default for model code and scripts, with documented exceptions. Ordinary exception authority and criteria remain to be defined; refusals and departures can be appealed to the Executive Board. Describe restrictions and reuse implications publicly. Board approval cannot supply missing rights or make restricted software open source. |
| Restricted models | Approved exceptions may permit public metadata records with separate metadata rights, accurate holdings, access conditions and review limits. Cases outside ordinary criteria can follow the Board appeal route. |
| Providers | ASU primary, Cloudflare fallback, with separate operator approval for each provider and use scope. |
| Local retention | Screening inputs and detailed results become eligible for deletion after three weeks and are removed at the next curator cleanup. This is a target, not a deletion deadline. |
| Moderation reconsideration | Contact-page intake, with manual fallback to `support@comses.net`. Curators handle requests; a different curator handles reconsideration of curator decisions or conflicts. The Board is the final internal appeal authority for unresolved or contested decisions. Record outcomes privately and explain decisions to requesters. No automatic review of every flag or response deadline is promised. |

Scientific peer review remains separate from moderation reconsideration. Public
accessibility does not mean public-domain dedication or waive contributor rights.

### Implementation and operating follow-up

Implementation is deferred from this content change. Track the following work
without presenting it as already deployed:

- Restrict spam-inference triggers and payloads to public content. Recheck
  visibility before sending queued requests and applying results. The current
  workflow can process private codebase information and nonpublic account signals.
- Persist the per-review AI choice, show it to reviewers and enforce it in the
  backend and tasks. Define preference changes, pending work and existing outputs.
  Provider exceptions must not override the opt-out.
- Define the metadata-only publication workflow, record labels, access controls,
  review/badge limits and identifier handling; this content change adds none.
- Assign cleanup responsibility and cadence, document deletion steps and retain
  enough moderation state to avoid restoring spam visibility when evidence is
  deleted. Define separate retention for logs, backups, exports, evaluation copies
  and AI review records.
- Assign contact/support monitoring, case assignment, private decision records,
  correction notices and Board escalation procedures. This route covers automated
  spam moderation; other conduct procedures need separate treatment.
- Complete the verification table and provider approval records. Do not infer
  production activation or human sign-off from the intended configuration.

## Decisions before adoption

The CoMSES Executive Board is the policy approval authority, with operational
responsibilities exercised by its delegated operators. This authority was
confirmed during gate review. Implementation work is deferred to a separate
follow-up and is not the next gate for drafting. Keep the distinctions between
proposed behavior and current capabilities visible while implementation catches
up; this decision does not verify deployed behavior or adopt the policies.

All new policy documents visibly identify themselves as unadopted drafts. The
scope, model-specific scripts, permanent dataset URLs, and transparent discretion
provisions carry forward the earlier discussion; the broader provisions are
proposals. Do not treat them as approved requirements merely because they sync.

- Record effective dates, revision history, operational delegations and the
  process for notifying users about material changes.
- Have the responsible operator review Terms of Use: legal entity, eligibility,
  assent, contributor hosting/preservation grant, disclaimers, liability,
  termination, governing law, and dispute resolution remain unresolved.
- Decide explicitly which policies, if any, are incorporated into the Terms and
  how versions and changes are handled. The index does not incorporate them.
- Confirm submission licenses, metadata and site-content licensing, rights
  complaints, preservation obligations, and withdrawal and citation continuity.
- Define review transparency, conflicts, confidentiality, appeals, and the limits
  of badges. Align existing review guidance and the FAQ with approved policy.
- Define moderation and conduct decision makers and an alternative reporting
  route for conflicts. Establish accessibility targets and a reporting alternative.
- Approve AI disclosure thresholds, provider/data handling controls, and human
  accountability before introducing service-operated AI processing.
- Establish a visible mechanism for justified exceptions on affected records.
  This content change does not implement exception fields, consent controls,
  or new moderation or AI processing behavior.
- Publish approved pages before adding navigation and contributor-facing links.

## Verification

```bash
make test TEST_ARGS='home.tests.test_policy_page home.tests.test_education_content_sync'
```

Use a disposable database through a Compose override for the standard test target.
Tests cover idempotency, draft/live isolation, preservation of metadata and page
identity, missing sources, type-conflict rollback, and unmanaged child retention.
The policy content check renders the canonical index, eight policy drafts and
privacy source with the site's Markdown renderer, then checks internal routes
and fragments within that collection, including generated heading IDs and
explicit HTML anchors. Existing contact, FAQ, review and digest routes are
explicitly allowed; their live content and anchors are outside this check.

On 2026-11-17, after cleanup, all 12 tests in `home.tests.test_policy_page`
passed via `make test TEST_ARGS=home.tests.test_policy_page` in a disposable
Compose project with copied source, synthetic credentials, isolated services and
storage, and no published ports. The target reused the cached `comses/server:dev`
image without rebuilding. The system check reported no issues. Ruff lint, format
checks and `git diff --check` also passed. Disposable services were removed
afterward; no CMS sync, publication or production verification was performed.
