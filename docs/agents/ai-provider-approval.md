# AI provider terms and operator approval

The CoMSES Executive Board sets policy; delegated human operators record provider
approval here. Implementation is separate follow-up work. These records support
the draft policies and do not adopt them or activate any service.

## Required terms

Review the applicable provider terms, institutional agreement or written
confirmation against the following requirements. Record the source and any
qualifications with the approval; a separately negotiated contract is not an
automatic requirement.

- **Private processing:** protect submitted inputs and outputs as confidential;
  use them to provide the requested inference service. Do not publish them,
  expose them to other customers or use them for unrelated purposes.
- **No training:** do not use submitted inputs or outputs for model training,
  fine-tuning or training datasets, including when the submitted content is public.
- **Minimum content retention:** retain inputs and outputs only as long as
  necessary to process the request and deliver the result. Identify any further
  retention for security, troubleshooting or legal obligations, its duration and
  who can access it. Do not equate retained usage metadata with retained content.
- **Limited access and recipients:** limit human access to necessary authorized
  personnel under confidentiality obligations. Identify subprocessors, onward
  services and any logging or caching that stores content; apply the same privacy
  and purpose restrictions to those recipients.
- **Account and use scope:** identify the service, account, endpoint, relevant
  settings and permitted data categories. Distinguish public-content spam screening
  from optional assessment or summarization of private peer-review materials.
- **Changes and incidents:** identify the provider's route for reporting an
  incident or material change to these terms, and the operator responsible for
  reassessing approval when the service, terms, recipients or approved use changes.

For this policy, "minimal retention" is a purpose limit, not an invented provider
deletion deadline. Record actual content-retention periods or exceptions when
confirmed. CoMSES's separate three-week curator-cleanup target does not describe
provider retention or require deletion of provider usage metadata on that schedule.

The intended arrangement is ASU primary and Cloudflare fallback. Approve each
provider and use scope explicitly; approving the primary does not approve the
fallback or authorize a broader class of data.

## Working assumptions

For drafting, assume ASU inference is private, inputs and outputs are not used for
training, and content is retained only to the minimum extent necessary for
inference. Proceed with the policy drafts on this basis. This is the agreed
working assumption, not a finding that ASU's account terms or deployment have
been verified or that an operator has signed off.

The previously checked [ASU documentation](https://docs.rc.asu.edu/ai/api/limits-and-errors/#usage-and-data-handling)
separately describes 180-day gateway usage records excluding prompt and response
text. Preserve that distinction when confirming the content-retention assumption.
[Cloudflare Workers AI documentation](https://developers.cloudflare.com/workers-ai/platform/data-usage/)
describes no training on customer content and limited standard-inference content
retention, with feature-specific handling and stated exceptions. Its applicable
account terms, settings and use scope still need explicit operator approval.

## Approval records

An operator approves a provider by checking its approval box and completing the
name, delegation, date, scope and evidence fields. Leave the box unchecked while
approval is pending. Do not infer approval from these working assumptions,
credentials being present, or a service already being enabled.

### ASU Research Computing: intended primary

- [ ] Explicitly approved by a delegated human operator for the scope below.
- Operator name and delegation: pending
- Approval date: pending
- Service/account/endpoint and relevant settings: pending
- Approved use and data categories: pending
- Supporting terms or written confirmation, version/date: pending
- Privacy and no-training conclusion: working assumption above; sign-off pending
- Content retention, exceptions, authorized access and recipients: pending
- Usage-metadata retention: documentation describes 180 days; account confirmation pending
- Conditions, review date or change triggers: pending
- Executive Board exception reference, if required: pending assessment

### Cloudflare Workers AI: intended fallback

- [ ] Explicitly approved by a delegated human operator for the scope below.
- Operator name and delegation: pending
- Approval date: pending
- Service/account/endpoint and relevant settings: pending
- Approved use and data categories: pending
- Supporting terms or written confirmation, version/date: pending
- Privacy and no-training conclusion: pending
- Content retention, exceptions, authorized access and recipients: pending
- Usage-metadata retention: pending
- Conditions, review date or change triggers: pending
- Executive Board exception reference, if required: pending assessment

## Exceptions

If required terms cannot be established or a departure is proposed, record the
uncertainty or departure, rationale, affected data, safeguards and review date.
The Executive Board must explicitly approve a documented exception before the
exceptional use. Record that decision with the provider approval and explain
material data-handling effects in the public disclosure.

Provider exceptions do not waive the public-only boundary for spam inference,
override a contributor's peer-review AI opt-out or supply rights CoMSES does not
hold. Operator approval covers only the recorded scope and conditions.
