> Draft for community and governance review. This document has not been adopted.

## Purpose and accountability

Proposed policy: allow useful AI assistance and automated processing while keeping research provenance, privacy, rights, and human accountability visible. These rules cover contributor use, reviewer assistance, service-operated processing, and bulk access by external systems. The planned use of ASU-hosted and Cloudflare-hosted models for spam detection is described in the [privacy policy](/about/data-privacy/). That proposal does not authorize every form of automated processing or reuse.

## Contributor disclosure

Disclose material use of AI or coding agents in model code, custom scripts, documentation, data preparation, analysis, or generated results. A short release note should identify the tool and model/version when known, period of use, task, affected artifacts, consequential changes, and human checks performed. Distinguish reported tool use from independently verified provenance; record unknown details as unknown. Routine spelling corrections do not need individual disclosure, and exhaustive prompt or interaction logs are not required.

Retain enough information to explain and reproduce consequential transformations, without exposing credentials, personal data, or confidential prompts. Identify synthetic data and generated example outputs. Authors remain responsible for accuracy, licensing, citations, and validation; an agent is not a substitute for an accountable contributor.

## Review and service-operated processing

Do not send private submissions, reviews, or personal information to an external AI service without authorization and an assessment of its data handling terms. Record material automated assistance in assessments, including the tool identity, inputs or their identifiers, checks performed, limitations, and human reviewer. Do not present an automated assessment as independent human verification.

Before introducing service-operated AI features, disclose their purpose, inputs, external providers, retention, and whether data may be used for training. Reconcile those disclosures with the [privacy policy](/about/data-privacy/). Set appropriate consent or other authorization, controls, and human review before use. This draft gives no blanket permission to train on deposits or private user information.

Proposed spam-screening boundary: deterministic, rule-based checks may operate on private drafts and public content within CoMSES. AI inference for spam screening is limited to publicly visible content and public fields. Private drafts, confidential reviews and nonpublic account information must not be sent for spam inference. A request to publish does not make still-private content eligible; inference may run once the content is public and when its public fields change.

The current implementation does not enforce this boundary: it can screen codebase information before publication and include nonpublic account signals. It is controlled by a site-wide setting, defaults to disabled and has no individual opt-in or opt-out control. Production activation has not been verified. Implementation follow-up includes visibility and payload restrictions, verification of deployed deterministic checks, and alignment of screening notices and authorization. This draft does not establish user consent.

For optional AI assessment or summarization during peer review, the proposed [review-request checkbox](/about/policy/review-publication/#ai-assistance-and-your-review-request) lets contributors opt out. The choice covers CoMSES-operated review assistance, including reviewer use, and is separate from spam screening and training. Disclosed assistance may process private release materials for a requested review when the contributor has not opted out and applicable permissions are in place. The control and enforcement still need implementation; requests without a recorded choice do not authorize AI assistance.

## Permissions and community expectations

Legal reuse permissions come from the applicable component licenses, any binding agreements and law. Our community expects clear provenance, appropriate credit and disclosure of material AI assistance. These expectations do not amend a deposit's license or establish that every downstream user has accepted the Terms. Follow the [licensing guidance](/about/policy/copyright-licensing/) for code, datasets and documentation separately.

A public deposit may be reused for AI training where its license or applicable law permits it. Publication makes it publicly accessible; it does not itself place the work in the public domain or change its license. Copyright exceptions and uses outside copyright can limit what a license controls. Third parties may collect public material for training or other inference, including uses that may be legally challengeable; CoMSES cannot guarantee prevention or undo rights already granted. Software subject to an AI-training or commercial-use ban must not be labeled open source under the [OSI Open Source Definition](https://opensource.org/osd). [Creative Commons' AI licensing guidance](https://creativecommons.org/cc-license-guidance/) explains why restrictive licensing may limit human reuse without preventing AI use.

## Provider commitments

Proposed requirement for CoMSES-operated inference: use providers whose applicable agreements prohibit training or fine-tuning on content CoMSES submits, including public content, unless the CoMSES Executive Board approves a documented exception before use. Verify that the restriction covers relevant subprocessors and the selected service and settings. Approval of this proposal and verification of provider agreements or approval of an exception are still required; this is not a claim that every configured provider already meets the requirement.

Require private processing of submitted inputs and outputs, access limited to necessary authorized personnel, and content retention limited to what is necessary for inference, with any additional retention or recipients documented. Delegated human operators explicitly approve the applicable terms and permitted uses for each provider. For drafting, the working assumption is that ASU meets these privacy, no-training and minimal-content-retention requirements; operator sign-off remains pending.

An exception record should identify the provider and purpose, affected information, applicable terms and uncertainties, reason for the exception, safeguards, approver and review date. Explain material effects on data handling in the public disclosure while protecting confidential details. Exceptions cannot grant rights CoMSES does not hold or waive applicable privacy obligations. The CoMSES Executive Board approves exceptions; the review process must be defined before adoption.

An exception to the provider no-training requirement does not authorize sending private content or nonpublic account information for spam inference or override a contributor's review opt-out.

These agreements would govern processing on CoMSES's behalf. They would not change contributor licenses or bind unrelated parties collecting public material independently. Provider retention, logging and deletion also need separate verification; a no-training commitment is not a no-retention guarantee. The [privacy disclosure](/about/data-privacy/#audit) records the supported screening workflow and the facts still requiring operator confirmation.

## How we handle data sent to AI services

For the planned spam-screening service, the [privacy policy](/about/data-privacy/#audit) explains what information would be checked, who would receive it, what could be kept, and how to request human review.

- **We choose what leaves the site.** CoMSES controls the information sent, the permitted services, and whether a backup provider may receive the same information.
- **Providers control their own systems.** Their service terms and settings govern processing and retention after they receive a request. Local deployment controls do not enforce deletion at a hosted provider.
- **Our records need their own rules.** The proposed service would keep screening inputs and results at CoMSES. Provider retention limits do not delete those records.
- **Screening and training are separate uses.** Permission to screen for spam does not establish permission to train or fine-tune a model on submissions. Any proposed training use needs its own review and disclosure.

Before activation, confirm the provider terms, local retention and deletion rules, and the way people can request review of an automated decision. Keep these details current when the service changes.

To challenge an automated spam classification, use the [contact page](/about/contact/) or, if the form is unavailable to you, email [support@comses.net](mailto:support@comses.net) for manual intake. The curator team handles requests, with a different curator reviewing prior curator decisions or conflicts, and the CoMSES Executive Board serving as final internal appeal authority for unresolved or contested decisions. The [privacy policy](/about/data-privacy/#audit) explains the process and private decision records. Scientific peer review uses the separate Request Peer Review workflow on the model detail page.

## Automated access and reuse

Follow the [Acceptable Use policy](/about/policy/acceptable-use/), access controls, and each artifact's license. Permission to download does not itself resolve permission for every downstream use. Identify automated clients where supported, avoid service disruption, and discuss large-scale processing with the team.

Crawler instructions and training-preference notices can communicate requests, but cannot guarantee exclusion from training datasets. Their legal effect depends on applicable law, rights-holder authority and any binding agreements. The [Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html) describes crawler directives as requests, not access authorization.

## Evolution and exceptions

Review this policy as tools and practices change. Publish dated revisions and explain material changes. Justified exceptions should identify the departure, reason, and implications visibly on the affected record or service notice while protecting sensitive details. Exceptions cannot waive rights held by others. Before adoption, define disclosure thresholds, approval responsibility, and how users can question or correct an automated result.
