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

## Content audits for spam and security vulnerabilities

As open access public infrastructure, CoMSES Net is unfortunately subject to spam and the other vagaries that rattle
about the internet. Due to the scale differential between submitted content and our small academic research software
engineering team, we automate analysis and classification of submitted content for spam and security vulnerabilities. If
you'd like to be a part of our moderation team or have any questions or concerns about our analyses,
please [contact us](/about/contact). These policies are regularly reviewed and approved by the CoMSES Executive Board.

### What is checked?

We analyze freeform text like codebase descriptions, job and event submissions, member profile updates, and forum content. In general, anything that you eventually intend to make public on comses.net may be scanned.

- **Submission information:** titles, descriptions, tags, links and relevant dates.
- **Account and Profile information:** usernames, names, biographies, research interests, affiliations, education and professional links.

Sensitive data like passwords and emails will never be transmitted but personal or sensitive information embedded in a description or another screened field could be included.

### Who processes the information?

We use locally hosted models on Arizona State University Research Computing cloud infrastructure. A Cloudflare-hosted Clef model may also serve as a backup when the primary service fails or takes too long. The same information may therefore reach both providers.

### What could be kept?

This table was last verified on November 9, 2026.

| Organization | Information kept and its purpose |
| --- | --- |
| **CoMSES Net** | Keep the screened text and metadata, the model used, and classification results to support moderation and evaluate detection quality. Retention period and deletion process are currently set to 3 weeks. |
| **ASU Research Computing** | Keeps request metadata, such as model, timing and usage counts, for 180 days. Those records exclude prompt and response text. This statement does not establish retention rules for every part of the service. [ASU data handling](https://docs.rc.asu.edu/ai/api/limits-and-errors/#usage-and-data-handling) |
| **Cloudflare Workers AI** | Standard inference inputs and outputs are kept only as needed to process the request and return the response, subject to stated exceptions. Logging, caching and other features that store content have separate rules; operational metadata may also be retained. [Cloudflare data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/) |


Cloudflare also states that it does not use Workers AI customer content to train models.

Sources: 
- [ASU data handling](https://docs.rc.asu.edu/ai/api/limits-and-errors/#usage-and-data-handling) 
- [Cloudflare data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/)

### What can CoMSES control?

We control which information we send, which services may receive it, whether a backup service is used, and what our application stores. After a provider receives a request, its own systems and service terms govern its handling of that information.

### What if the system makes a mistake?

An automated decision could hide flagged content from public listings without additional human review. If you believe your content has been incorrectly flagged, [please contact us](/about/contact/) to request human review.

## Disclosure to Third Parties

We use [Google Analytics](https://policies.google.com/privacy?hl=en).

Our [content screening services](#audit) send selected submission and profile information to open weights models hosted and maintained by ASU Research Computing's Voyager service and [Cloudflare Clef](https://developers.cloudflare.com/workers-ai/models/clef/).

## How does CoMSES secure your data?

- We use the security protections provided by our authentication framework to safeguard account credentials.
- All web resources are only accessible over https
- We patch and update our systems as soon as possible when security vulnerabilities in our technology stack are reported. We monitor CVEs and security mailing lists to help us keep our dependencies up to date.

## Use of Cookies

Cookies are used on this website for authentication as well as tracking page views and downloads. You may opt out of Google Analytics tracking with a [browser addon](https://tools.google.com/dlpage/gaoptout/).

## What personal information is stored on our site?

We store information supplied by you or other contributors, as well as the technical information described above. The planned spam-screening workflow would also store screening inputs and classification results as described above. Personally entered information in your user profile can be deleted from the website at any time by editing your user profile. If someone else has entered sensitive information about you on our website and you would like it removed please [contact us](/about/contact/).
