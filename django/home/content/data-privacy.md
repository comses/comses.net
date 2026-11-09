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
        - Archiving a codebase / codebase release
        - Posting comments in our [forum](https://forum.comses.net/)

## What do we do with this information?

- track user engagement to help us improve our website layout and organization of content
- summarize jobs, events, published computational models, and other content for the [comses digest](/digest/)
- provide aggregate statistics for reports and grant proposals to funding agencies
- provide a (hopefully!) useful service to the computational modeling community

<a id="automated-spam-detection"></a>

## Automated spam detection

**Status: planned, pending deployment and review.** This section describes the proposed service. It does not mean that model-assisted screening is already enabled.

### What would be checked?

The service would check new model-library entries, job and event submissions, and member-profile updates for spam. Checks may occur before a model-library entry is published.

- **Submission information:** titles, descriptions, tags, links and relevant dates.
- **Profile information:** names, biographies, research interests, affiliations, education and professional links.
- **Account information:** usernames, signup timing and the names of linked-account providers.

Uploaded model files, passwords and dedicated account email fields would not be sent in the screening request. Personal information written into a description or another screened field could still be included.

### Who would process the information?

The proposed setup uses models hosted by Arizona State University Research Computing. If configured, a Cloudflare-hosted Clef model can serve as a backup when the primary service fails or takes too long. The same information may therefore reach both providers.

### What could be kept?

The table distinguishes our planned records from the providers' published descriptions, checked on November 9, 2026.

| Organization | Information kept and its purpose |
| --- | --- |
| **CoMSES Net** | Would keep the screened text and metadata, the model used, and classification results to support moderation and evaluate detection quality. The retention period and deletion process still need to be set before activation. |
| **ASU Research Computing** | Says its gateway keeps request metadata, such as model, timing and usage counts, for 180 days. Those records exclude prompt and response text. This statement does not establish retention rules for every part of the service. |
| **Cloudflare Workers AI** | Says standard inference inputs and outputs are kept only as needed to process the request and return the response, subject to stated exceptions. Logging, caching and other features that store content have separate rules; operational metadata may also be retained. |

Sources: [ASU data handling](https://docs.rc.asu.edu/ai/api/limits-and-errors/#usage-and-data-handling) and [Cloudflare data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/).

Cloudflare also states that it does not use Workers AI customer content to train models. We have not established an equivalent training-use statement for the ASU service from the documentation reviewed. Using a model to classify a submission does not itself mean that the model is trained on it.

### What can CoMSES control?

We control which information we send, which services may receive it, whether a backup service is used, and what our application stores. After a provider receives a request, its own systems and service terms govern its handling of that information. Our deployment settings cannot by themselves enforce deletion from a provider's systems.

A provider's limited retention does not remove copies kept by CoMSES. Before activation, we need to confirm the deployed services' data-handling terms and our own retention and deletion rules.

### What if the system makes a mistake?

An automated decision could hide flagged content from public listings without prior human review. If you believe your content has been incorrectly flagged, [contact us](/about/contact/) to request human review.

## Disclosure to Third Parties

We use [Google Analytics](https://policies.google.com/privacy?hl=en).

The [planned spam-screening service](#automated-spam-detection) would also send selected submission and profile information to ASU Research Computing and, when configured, Cloudflare. That section explains what would be sent and what each organization may retain.

## How does CoMSES secure your data?

- We use the security protections provided by our authentication framework to safeguard account credentials.
- All web resources are only accessible over https
- We patch and update our systems as soon as possible when security vulnerabilities in our technology stack are reported. We monitor CVEs and security mailing lists to help us keep our dependencies up to date.

## Use of Cookies

Cookies are used on this website for authentication as well as tracking page views and downloads. You may opt out of Google Analytics tracking with a [browser addon](https://tools.google.com/dlpage/gaoptout/).

## What personal information is stored on our site?

We store information supplied by you or other contributors, as well as the technical information described above. The planned spam-screening workflow would also store screening inputs and classification results as described above. Personally entered information in your user profile can be deleted from the website at any time by editing your user profile. If someone else has entered sensitive information about you on our website and you would like it removed please [contact us](/about/contact/).
