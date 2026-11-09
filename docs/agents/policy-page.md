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
head `68b1835e4c7821775ce7c47f4ab7a5438f5ee48e`. The PR was open and unmerged.
Detection defaults to disabled; the proposed defaults use ASU Research Computing
(`gemma4-31b-it`) with Cloudflare (`clef-omni`) as a fallback. Providers and models
are configurable. Do not describe this as processing confined to the CoMSES web
server or as an already enabled production feature.

`spam_check_content` in `core/models.py` and `library/models.py` selects submission
metadata, profile fields, usernames, signup timing and linked-account provider
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

### Provider documentation checked on 2026-11-09

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

## Decisions before adoption

All new policy documents visibly identify themselves as unadopted drafts. The
scope, model-specific scripts, permanent dataset URLs, and transparent discretion
provisions carry forward the earlier discussion; the broader provisions are
proposals. Do not treat them as approved requirements merely because they sync.

- Identify the policy owner, approval authority, effective dates, revision history,
  and process for notifying users about material changes.
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
  moderation workflows, or an AI processing service.
- Publish approved pages before adding navigation and contributor-facing links.

## Verification

```bash
make test TEST_ARGS='home.tests.test_policy_page home.tests.test_education_content_sync'
```

Use a disposable database through a Compose override for the standard test target.
Tests cover idempotency, draft/live isolation, preservation of metadata and page
identity, missing sources, type-conflict rollback, and unmanaged child retention.
