## Who manages the data?

CoMSES Net is an open-source community supported by volunteers and paid staff. Our principal investigators, Executive Board and developers share responsibility for protecting your data. Please [contact us](/about/contact/) with privacy or security concerns.

## What information is collected when you visit this site?

We collect technical information about visits and downloads, along with content you post:

- IP addresses in server logs, used to respond to denial-of-service attacks and other abuse through tools such as [fail2ban](https://www.fail2ban.org/).
- Information about model downloads, used to help distinguish bots from people.
- Website usage information through Google Analytics. Its [IP-handling guidance](https://support.google.com/analytics/answer/2763052?hl=en) describes its anonymization practices; our live configuration still needs to be checked.
- Content you submit, including jobs, events, model releases and comments in our [forum](https://forum.comses.net/).

## What do we do with this information?

We use it to improve the site, prepare the [CoMSES Digest](/digest/), report aggregate statistics to funders and support the computational modeling community. Spam screening, when enabled, uses the information described below.

<a id="audit"></a>

## Automated screening for spam

!!! info "Draft update for approval"
    The screening policy below is proposed. The current software does not yet enforce it, and operators still need to confirm what is running on the live site.

We propose allowing ordinary rule-based checks on private drafts and public content within CoMSES. AI spam checks would use only publicly visible content and fields, including public profile fields. They must exclude private drafts, confidential reviews and nonpublic account information. A request to publish is not enough: content must already be public before it is sent for AI spam screening, including checks after public-field changes.

AI screening is disabled by default and controlled by a site-wide setting, with no individual opt-in or opt-out. We have not confirmed whether it is enabled on the live site. The current software can screen models before publication and send nonpublic account information; this must change to meet the proposed policy.

### What is checked?

The proposed checks cover public model descriptions and metadata, job and event posts, and public profile fields. The current software selects:

- **Submission information:** titles, summaries, descriptions, tags, links, event locations and dates; model replication notes, references and associated-publication text; submission time, submitter username, time between signup and submission, and linked-account provider names.
- **Profile information:** username, account join time, name, biography, research interests, affiliations, degrees, industry, tags, personal and professional links, and linked-account provider names.

These requests do not select uploaded model files, passwords or dedicated email fields. Text people write can still contain email addresses or sensitive information. The list describes the software, not a verified account of live requests. Operators must restrict requests to public fields and check any separate forum screening before describing it here.

### Who processes the information?

We plan to use ASU Research Computing first, with Cloudflare Workers AI as a separately approved fallback. The software supports both. If ASU fails or takes too long, both may receive the same content. Settings and available credentials can change which service receives a request; live recipients and request routes still need confirmation.

### What could be kept?

Provider documentation was checked on November 19, 2026. It does not verify our account settings, operator approvals or completed deletions.

| Organization | Screening records and retention |
| --- | --- |
| **CoMSES Net** | The software stores screening inputs, model identity, spam score and cutoff, response time and fallback errors for moderation and evaluation. Curators will delete inputs and detailed results at their next cleanup after 3 weeks. This is a target, not a deletion deadline; records may remain longer between cleanups. Curator assignments, cadence, deletion scope and cleanup records still need confirmation. |
| **ASU Research Computing** | This draft assumes private inference, no training on inputs or outputs, and content kept only as needed for inference. Operator approval is pending. ASU documents separate gateway usage records kept for 180 days without prompt or response text; that period does not describe content retention. [ASU data handling](https://docs.rc.asu.edu/ai/api/limits-and-errors/#usage-and-data-handling) |
| **Cloudflare Workers AI** | Its documentation says standard inference content is kept for processing and delivery, with stated exceptions, and is not used for training. Features that save state, logging, caching and usage records have separate rules. Our agreement and selected features still need operator approval. [Cloudflare data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/) |

Fallback errors are logged, and task failures can reach error-reporting services. Logs, backups, exports and evaluation copies may have separate recipients and retention. Deleting a moderation record does not establish that these copies were deleted.

### What can CoMSES control?

We choose what to send, which providers may receive it, whether to use a fallback and what to store locally. Providers handle requests under their own systems and terms. Our draft [AI policy](/about/policy/#ai-and-automation) requires no-training agreements even for public inputs. Documented exceptions need Board approval before use. These requirements await policy approval and do not control independent uses of public deposits under their licenses or the law.

Before publishing this disclosure as current practice, operators must confirm live settings, field selection, providers and fallback routes, agreements, additional recipients, logs and retention. Provider documentation alone does not establish how our application handles data. Any approved exception affecting data handling must be explained here.

### What if the system makes a mistake?

When enabled, screening can hide content from public listings before human review. Moderators can reverse classifications, and automated checks preserve their decisions. If your content was wrongly flagged, use our [contact page](/about/contact/) or email [support@comses.net](mailto:support@comses.net) if you cannot use the form. Include the content link or identifier and a brief explanation, without passwords or unnecessary sensitive information.

Under the proposed process, curators handle these requests. A different curator reconsiders a curator's decision or handles a conflict of interest. Unresolved or contested decisions can be appealed to the Executive Board as the final internal authority. We would keep private outcome and correction records and explain decisions to the requester. We cannot promise a response time or automatically review every flag. Intake monitoring, case assignment, records and appeals still need to be put in place.

Scientific peer review is separate: use **Request Peer Review** on your model's detail page.

## Disclosure to Third Parties

We use [Google Analytics](https://policies.google.com/privacy?hl=en). When enabled, [spam screening](#audit) sends selected information to configured ASU Research Computing or Cloudflare Workers AI services. Operators must confirm live recipients, including logging and error-reporting services.

### Proposed AI assistance during peer review

We plan a checkbox on the [peer review request](/education/sharing-models/#request-peer-review) to opt out of AI assessment and summarization by CoMSES and its reviewers. It is not implemented yet. Review assistance may use private release materials only for the stated review purpose, with the necessary permissions and if you have not opted out. Confidential reviewer correspondence needs separate permission. Older requests without a recorded choice do not authorize AI assistance.

Before enabling this feature, we must explain what is sent, to whom, what is kept, how people check results and what happens if you change your choice. The spam-screening details above do not describe the handling of a future review feature.

## How does CoMSES secure your data?

We use our authentication framework's security protections for account credentials, serve the site over HTTPS and monitor vulnerability reports for our software dependencies. We apply security updates as soon as possible.

## Use of Cookies

We use cookies for authentication and tracking page views and downloads. You can opt out of Google Analytics tracking with its [browser add-on](https://tools.google.com/dlpage/gaoptout/).

## What personal information is stored on our site?

We store information you or other contributors provide, along with the technical information described above. The proposed spam checks would also keep the inputs and results described in this draft. You can remove information you entered in your profile by editing it. If someone else has posted sensitive information about you, please [contact us](/about/contact/) to request its removal.
