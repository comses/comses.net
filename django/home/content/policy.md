!!! info "Draft for community review"
    These policies await Executive Board approval. They cover sharing models, using the site and our proposed Terms of Use. Planned AI features are marked below.

CoMSES Net is an open science gateway for computational modeling in the social and ecological sciences, governed by an [Executive Board](/about/people/) that drafts and approves these policies.

**On this page:** [Sharing a model](#sharing-a-model) · [Credit and licenses](#credit-and-licenses) · [Metadata](#metadata) · [Review and publication](#review-and-publication) · [Preservation](#preservation-and-withdrawal) · [Continuity](#service-continuity) · [Terms of Use](#terms-of-use) · [AI and automation](#ai-and-automation) · [Questions](#questions-and-decisions)

## Sharing a model

We welcome computational models across the social and ecological sciences. CoMSES began as openabm.org, with a focus on agent-based models; we now welcome other modeling approaches too. Standalone datasets, general purpose software and scripts unrelated to these models are outside the Model Library's scope and may be removed.

Models should include source code, narrative documentation and scripts for data preparation, simulations and analysis. Describe the environment, dependencies, parameters and a representative run. Link important input and example output datasets through permanent URLs and explain any access restrictions. Compiled executables are generally not permitted; curators may reject them before publication. Published files follow the withdrawal process below.

See our [contributor guide](/education/sharing-models/) for checklists, licenses and AI disclosure examples.

### What does not belong

We may decline or remove spam, advertising, phishing, malware and submissions that misrepresent their research basis, authorship or review status. Disputed assumptions or findings alone are not grounds for removal. Curators assess research-integrity concerns; an automated spam flag does not establish misconduct.

Curators may approve a public metadata record for a model with restricted files. It must explain the research, access conditions, what CoMSES holds and any limits on review or preservation. A short description without model files is otherwise not a normal deposit.

## Credit and licenses

Credit everyone who contributed substantially, and agree on authors and contributor roles before publication. Name a contact for the release. Ask curators about unresolved credit disputes; corrections must preserve accurate citation history. Authorship does not necessarily mean copyright ownership.

You keep ownership of your work and must have permission to share it. Identify the licenses covering code, data and documentation, preserve third-party notices, and check unclear permissions with the rights holder and a curator. Our proposed hosting permission is described under [Terms of Use](#terms-of-use).

We require OSI-approved licenses for model code and scripts unless curators approve a documented exception. [Contact us](/about/contact/) to discuss one. Refusals and exceptional cases can be appealed to the Executive Board. Approval cannot supply missing rights or make a restricted license open source.

See the [contributor guide](/education/sharing-models/#choose-licenses-by-component) for license recommendations and examples.

## Metadata

For each release, provide a title, contributors and roles, version, description, licenses, dependencies and related research. We keep separate model and release records, with exports in CodeMeta, citation-file and DataCite DOI formats. Our [metadata schema](https://github.com/comses/comses.net/blob/main/docs/source/metadata_schema.md) describes the fields and identifiers.

Public metadata helps people find and cite models, including those with restricted files. Public access alone does not grant reuse permission. A metadata reuse license, its exclusions and contributor permissions still need Board approval. This draft assigns no blanket license to existing metadata or deposits.

## Review and publication

Use **Request Peer Review** on your model's detail page to request optional scientific peer review. Review covers execution, documentation and code quality against baseline criteria. It does not certify scientific validity or suitability for a particular use. Reviewers must disclose conflicts, protect private materials and explain what they checked.

Each release must pass peer review for its own DOI. New versions need their own review and DOI. Releases remain private during review. Published files cannot be changed in place; file changes require a new release. Metadata corrections need no new review, but must preserve accurate version-specific citations and existing DOIs.

Records for restricted files must say whether CoMSES could run, review or preserve them. See the [review instructions](/reviews/) for the procedure.

## Preservation and withdrawal

We aim to preserve published releases and metadata, including older versions, for the lifetime of the service. We cannot promise that software will always run, so please keep your own copies. The [privacy page](/about/data-privacy/#audit) describes a separate cleanup target for spam-screening records, not archived models.

Withdrawal is exceptional, for example when confidentiality, privacy or licensing problems arise. [Contact us](/about/contact/) or email [support@comses.net](mailto:support@comses.net) with the record and reason. Authorized operators assess requests and may restrict access while resolving a concern. Where lawful, we keep a public citation record explaining the withdrawal and keep the DOI resolving to it. A DOI is never reassigned to another work.

## Service continuity

If CoMSES can no longer sustain the service, we propose that the Board and its authorized operators seek a suitable repository for published files and metadata, respecting permissions and access restrictions. We would maintain identifier resolution where possible and notify contributors of significant changes. No successor or transfer date is guaranteed. The Board must confirm resources, responsibilities and transfer arrangements before adopting this plan.

## Terms of Use

Keep your account information accurate, protect your credentials and treat others with respect. Harassment, threats, impersonation, retaliation, spam and unauthorized sharing of personal or confidential information are unacceptable.

Access only accounts and materials you are authorized to use. Do not bypass access controls, disrupt the service or distribute malicious code. Discuss research software with potentially harmful behavior with curators before submitting it. Identify automated clients where supported, and contact us before bulk activity that could affect availability.

We need permission to host, preserve, display, distribute and technically process your contributions for the service. What this permission covers, how long it lasts and how it applies to private or withdrawn deposits still need approval. It is separate from the license you offer others and gives no general permission to train AI models.

You are responsible for your contributions and for assessing materials you download. Peer review does not guarantee accuracy, continued operation or fitness for your intended use.

This section is the proposed agreement with users. Other sections describe repository policies and community expectations; they do not automatically become part of that agreement. Before adoption, the Board must confirm the legal operator, Terms acceptance, any included sections, effective dates and change notices. Links alone do not incorporate the privacy page or contributor guide into the Terms.

## AI and automation

AI tools can assist research, but authors remain responsible for the work. Describe these tools in your methods or disclosure; do not list them as authors or contributors. Document the research purpose, methods and checks for generated code, synthetic data and other outputs, including research on generative models. Do not present synthetic data or generated images as empirical observations, or invented citations and findings as evidence.

Describe significant AI assistance with code, documentation, data or results, and explain how you checked it. Routine spelling corrections do not need disclosure, and exhaustive prompt logs are not required. You remain responsible for accuracy, permissions and research claims.

!!! info "Public access and AI use"
    Publishing a model does not put it in the public domain or change its license. Others may collect public material for AI training or inference. Some uses may be allowed by the license or law; others may be legally challenged. We cannot guarantee prevention. This notice grants no additional permissions and waives none of your rights.

Our proposed spam policy allows rule-based checks on private content within CoMSES. AI spam checks would use only public content and fields. Flags may hide content from public listings before human review; you can ask curators to reconsider.

For optional AI assessment or summarization during peer review, we plan an unchecked **“Do not use AI to assess or summarize this release during peer review”** checkbox. The choice covers CoMSES and its reviewers and grants no training permission. The checkbox and spam restrictions still need implementation. Older requests without a recorded choice do not authorize AI assistance.

We plan to use ASU Research Computing, with Cloudflare as a separately approved fallback. Providers must protect inputs and outputs, keep content only as needed for inference, and agree not to train or fine-tune on it, including public inputs. Authorized operators must explicitly approve each provider's terms and uses. The Board may approve documented exceptions, but these cannot override a review opt-out, allow private content in AI spam checks or supply missing rights. See [privacy](/about/data-privacy/#audit) for data handling, working assumptions and outstanding checks.

## Questions and decisions

Please report rights, security, accessibility or conduct concerns privately through our [contact page](/about/contact/) or [support@comses.net](mailto:support@comses.net). Include enough detail to help without unnecessary sensitive information. We may request corrections, restrict access or remove harmful content. Urgent action may come before notice.

<a id="accessibility"></a>

!!! info "Accessibility"
    We want everyone to be able to use CoMSES. If a page or task is inaccessible, [contact us](/about/contact/){.alert-link} or email [support@comses.net](mailto:support@comses.net){.alert-link}. We will work with you on a practical alternative while addressing the problem.

Curators handle requests to review automated spam decisions. A different curator handles reconsideration of a curator's decision or a conflict of interest. Unresolved or contested decisions can be appealed to the Executive Board as the final internal authority. We keep private outcome and correction records and explain decisions to the requester. We cannot promise a response time or automatically review every flag.
