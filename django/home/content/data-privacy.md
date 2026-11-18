## Who manages the data?

The PIs, executive board, and software developers behind [CoMSES Net, the Network for Computational Modeling in the Social and Ecological sciences](/about/contact/) value your privacy and take security issues seriously. We are an open-source volunteer-driven community but we also have paid staff who are responsible for ensuring the security and privacy of your data.

## What information is collected when you visit this site?

When you visit this site we track:

- IP addresses
        - [pseudo-anonymized](https://support.google.com/analytics/answer/2763052?hl=en) via Google Analytics
        - in HTTP server logs to help us handle Denial of Service and other brute force hacks via [fail2ban](https://www.fail2ban.org/)
        - when a codebase release is downloaded to help us disambiguate bots from real users
- Site content which includes:
        - Posting a job or event
        - Publishing a codebase release
        - Posting comments in our [forum](https://forum.comses.net/)

## What do we do with this information?

- track user engagement to help us improve our website layout and organization of content
- summarize jobs, events, published computational models, and other content for the [comses digest](/digest/)
- provide aggregate statistics for reports and grant proposals to funding agencies
- provide a (hopefully!) useful service to the computational modeling community

<a id="audit"></a>

## Automated screening for spam

> Draft update for approval. This section distinguishes the proposed screening policy from current capabilities. Implementation changes are tracked separately; descriptions of deployed behavior require operator verification.

Proposed policy: deterministic, rule-based spam checks may run on private drafts and public content within CoMSES. AI inference for spam detection is limited to publicly visible content and public fields, including public profile fields. Private drafts, confidential reviews and nonpublic account information are excluded from spam inference. A request to publish does not itself make private content eligible; inference may run after public visibility begins and when public fields change.

The current inference workflow does not enforce that boundary. Detection defaults to disabled and is controlled by a site-wide setting, with no individual opt-in or opt-out control. Production activation has not been verified. Follow-up work includes aligning screening triggers and payloads with the proposed boundary, verifying deployed deterministic checks, and confirming the authorization model and any user controls.

### What is checked?

The proposed inference workflow would screen public codebase descriptions and metadata, job and event posts, and public profile fields. The following list describes the current payload, which requires changes before it meets the proposed policy: the current workflow can screen new codebases before publication and includes nonpublic account signals.

- **Submission information:** selected titles, summaries, descriptions, tags, links, event locations and relevant dates; codebase replication notes, references and associated-publication text; submission time, submitter username, time between signup and submission, and linked-account provider names.
- **Profile information:** username, account join time, name, biography, research interests, affiliations, degrees, industry, tags, personal and professional links, and linked-account provider names.

Uploaded model files, passwords and dedicated email fields are not selected for these screening requests. Screened text can contain email addresses or other personal or sensitive information. Operator check: restrict every inference payload to publicly visible fields, removing nonpublic account signals and private material; confirm the deployed selection and any separate forum-screening process before adding it to this disclosure.

### Who processes the information?

The implementation supports models hosted by Arizona State University Research Computing and Cloudflare Workers AI. Defaults select ASU as primary and Cloudflare as a fallback, but providers and models are configurable. If the primary service fails or takes too long, the same selected content can reach both providers. Available credentials also affect which configured service receives a request. Operator check: confirm the active services, request paths and fallback configuration; these defaults do not establish the production recipients.

### What could be kept?

Provider documentation was checked on November 17, 2026. The table distinguishes that documentation from the local retention proposal; it does not verify deployed settings or completed deletions.

| Organization | Information kept and its purpose |
| --- | --- |
| **CoMSES Net** | The implementation stores full screening inputs, model identity, classification score and threshold, latency, and fallback error details for moderation and evaluation. Human curators will manually manage retention and deletion. Screening inputs and detailed results become eligible for deletion after 3 weeks and are removed during the next curator cleanup. This is a cleanup target, not a guaranteed deletion deadline; records may remain longer until cleanup occurs. Responsible curators, cleanup cadence, deletion scope and records of completed deletions require confirmation. |
| **ASU Research Computing** | For drafting, we assume private inference, no use of submitted inputs or outputs for training, and content retention limited to what is necessary for inference. Explicit human-operator approval of these terms remains pending. ASU documentation separately describes gateway usage records retained for 180 days without prompt or response text; this is not a 180-day content-retention claim. [ASU data handling](https://docs.rc.asu.edu/ai/api/limits-and-errors/#usage-and-data-handling) |
| **Cloudflare Workers AI** | Its documentation limits standard inference content retention to request processing and delivery, subject to stated exceptions, and says customer content is not used for training. Stateful features, logging, caching and operational metadata have separate rules. Operator check: confirm the applicable agreement and selected features. [Cloudflare data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/) |

Fallback errors are also logged, and task failures can reach configured error-reporting services. Operator check: identify recipients and retention for application logs, error reports, backups, exports and evaluation copies; deletion of a moderation record does not establish deletion of those copies.

### What can CoMSES control?

We control which information we send, which services may receive it, whether a backup service is used, and what our application stores. After a provider receives a request, its own systems and service terms govern its handling of that information.

The [AI policy](/about/policy/ai-automated-processing/#provider-commitments) proposes requiring no-training agreements for CoMSES-operated inference, including public inputs, with documented exceptions approved by the CoMSES Executive Board before use. The proposed requirement still needs policy approval. Operator check: verify each provider's applicable agreement or approved exception and disclose material effects on data handling. This does not establish that unrelated parties cannot use public deposits under their licenses or applicable law.

### What if the system makes a mistake?

When screening is enabled, a spam classification can hide flagged content from public listings without prior human review. Moderators can overturn classifications, and automated checks preserve manual decisions. If you believe your content has been incorrectly flagged, request moderation reconsideration through the [contact page](/about/contact/). If you cannot use the form, email [support@comses.net](mailto:support@comses.net) for manual intake. Include a link or identifier for the affected content and a brief explanation; do not send passwords or unnecessary sensitive information. This is separate from scientific peer review, which is requested through the Request Peer Review button on the model detail page.

Under the proposed process, the curator team handles these moderation requests. A different curator reviews the case when reconsidering a curator's decision or when the original handler has a conflict of interest. Unresolved or contested decisions may be appealed to the CoMSES Executive Board as the final internal appeal authority. Record the outcome and any correction privately and send an explanation to the requester. This draft does not promise automatic review of every classification or a response deadline. Operator check: establish monitoring coverage for both intake routes and the procedures for assignment, private decision records, corrections and Board escalation.

## Disclosure to Third Parties

We use [Google Analytics](https://policies.google.com/privacy?hl=en).

When enabled, the supported [content screening workflow](#audit) sends selected submission and profile information to configured ASU Research Computing or Cloudflare Workers AI services. Production recipients and any additional logging or error-reporting services remain subject to the operator checks above.

### Proposed AI assistance during peer review

The proposed [peer review request](/about/policy/review-publication/#ai-assistance-and-your-review-request) would offer a checkbox to opt out of CoMSES-operated AI assessment and summarization. This control is not implemented. This review assistance is separate from public-content spam inference and may involve private release materials only for the disclosed review purpose, when the contributor has not opted out and applicable permissions are in place. Historical requests without a recorded choice do not authorize it. Operator check: identify and disclose review inputs, providers, retention, human checks and preference-change handling before enabling the feature. The spam-screening provider and retention descriptions above do not establish how a future review feature will handle data.

## How does CoMSES secure your data?

- We use the security protections provided by our authentication framework to safeguard account credentials.
- All web resources are only accessible over https
- We patch and update our systems as soon as possible when security vulnerabilities in our technology stack are reported. We monitor CVEs and security mailing lists to help us keep our dependencies up to date.

## Use of Cookies

Cookies are used on this website for authentication as well as tracking page views and downloads. You may opt out of Google Analytics tracking with a [browser addon](https://tools.google.com/dlpage/gaoptout/).

## What personal information is stored on our site?

We store information supplied by you or other contributors, as well as the technical information described above. The planned spam-screening workflow would also store screening inputs and classification results as described above. Personally entered information in your user profile can be deleted from the website at any time by editing your user profile. If someone else has entered sensitive information about you on our website and you would like it removed please [contact us](/about/contact/).
