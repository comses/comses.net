> Draft for community and governance review. This document has not been adopted.

## Purpose and accountability

Proposed policy: allow useful AI assistance and automated processing while keeping research provenance, privacy, rights, and human accountability visible. These rules cover contributor use, reviewer assistance, service-operated processing, and bulk access by external systems. The planned use of ASU-hosted and Cloudflare-hosted models for spam detection is described in the [privacy policy](/about/data-privacy/). That proposal does not authorize every form of automated processing or reuse.

## Contributor disclosure

Disclose material use of AI or coding agents in model code, custom scripts, documentation, data preparation, analysis, or generated results. Record the tool or agent identifier, model and version when known, date or period of use, task, affected artifacts, and the human checks performed. Distinguish reported tool use from independently verified provenance; record unknown details as unknown. Routine spelling corrections need not produce an exhaustive interaction log.

Retain enough information to explain and reproduce consequential transformations, without exposing credentials, personal data, or confidential prompts. Identify synthetic data and generated example outputs. Authors remain responsible for accuracy, licensing, citations, and validation; an agent is not a substitute for an accountable contributor.

## Review and service-operated processing

Do not send private submissions, reviews, or personal information to an external AI service without authorization and an assessment of its data handling terms. Record material automated assistance in assessments, including the tool identity, inputs or their identifiers, checks performed, limitations, and human reviewer. Do not present an automated assessment as independent human verification.

Before introducing service-operated AI features, disclose their purpose, inputs, external providers, retention, and whether data may be used for training. Reconcile those disclosures with the [privacy policy](/about/data-privacy/). Set appropriate consent or other authorization, controls, and human review before use. This draft gives no blanket permission to train on deposits or private user information.

## How we handle data sent to AI services

For the planned spam-screening service, the [privacy policy](/about/data-privacy/#automated-spam-detection) explains what information would be checked, who would receive it, what could be kept, and how to request human review.

- **We choose what leaves the site.** CoMSES controls the information sent, the permitted services, and whether a backup provider may receive the same information.
- **Providers control their own systems.** Their service terms and settings govern processing and retention after they receive a request. Local deployment controls do not enforce deletion at a hosted provider.
- **Our records need their own rules.** The proposed service would keep screening inputs and results at CoMSES. Provider retention limits do not delete those records.
- **Screening and training are separate uses.** Permission to screen for spam does not establish permission to train or fine-tune a model on submissions. Any proposed training use needs its own review and disclosure.

Before activation, confirm the provider terms, local retention and deletion rules, and the way people can request review of an automated decision. Keep these details current when the service changes.

## Automated access and reuse

Follow the [Acceptable Use policy](/about/policy/acceptable-use/), access controls, and each artifact's license. Permission to download does not itself resolve permission for every downstream use. Identify automated clients where supported, avoid service disruption, and discuss large-scale processing with the team.

## Evolution and exceptions

Review this policy as tools and practices change. Publish dated revisions and explain material changes. Justified exceptions should identify the departure, reason, and implications visibly on the affected record or service notice while protecting sensitive details. Exceptions cannot waive rights held by others. Before adoption, define disclosure thresholds, approval responsibility, and how users can question or correct an automated result.
