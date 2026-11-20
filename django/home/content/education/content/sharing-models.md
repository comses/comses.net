Use this guide to prepare your model, choose licenses and describe AI assistance. Our draft [CoMSES Policies](/about/policy/) set out the proposed rules; this guide adds no license conditions.

**On this page:** [Preparation](#prepare-the-deposit) · [Licenses](#choose-licenses-by-component) · [AI disclosure](#disclose-material-ai-assistance) · [Peer review](#request-peer-review)

## Prepare the deposit

- Include model source code and the custom scripts used to prepare data, run simulations and analyze results.
- Document software and dependency versions, installation, parameters, random seeds where relevant, and a representative run with expected outputs.
- Name contributors and their roles, identify the model version and related research, and describe known limitations.
- For important input and example output datasets, give permanent links, versions, sources and access conditions. If you cannot share the data, explain how to request access and provide a synthetic or reduced example where possible.
- Explain accessibility or platform limitations. Where useful, offer an alternative description or sample results.

The [responsible practices modules](/education/responsible-practices/) cover documentation and research software practices in more detail.

## Choose licenses by component

Check who owns each part, including any employer or institution rights. Preserve third-party terms and check dependency compatibility. Ask the rights holder and a curator about unclear permissions before sharing material.

| Material | Suggested licenses | Check before choosing |
| --- | --- | --- |
| Code and custom scripts | [MIT](https://opensource.org/license/mit) for a short permissive license; [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) for permissive reuse with an express patent grant and related conditions. Consider [GPL-3.0](https://opensource.org/license/gpl-3.0) for copyleft obligations on distribution of covered software. | Employer and collaborator permissions, notices, dependencies and compatibility with the combined work. All three permit commercial use. |
| Datasets | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en) when authorized to waive copyright and database rights, or [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en) when attribution should be a license condition. | Rights in the database and its contents, third-party permissions, privacy, confidentiality and access conditions. These tools do not clear missing rights. |
| Documentation, figures and tutorials | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en) for reuse and adaptation with attribution. | Separately licensed images, quotations, papers and embedded code. Use a suitable software license for code examples where appropriate. |

In your release README, list the licenses and the files each covers. Check each part before applying one license to the whole deposit. Linked datasets keep their own licenses and access conditions. Cite your sources even when a license does not require it.

!!! info "Restrictions on AI use"
    Software licenses that restrict commercial use or AI training do not meet the [OSI Open Source Definition](https://opensource.org/osd){.alert-link}. Describe any restrictions clearly and ask a curator about an exception. A no-training notice cannot prevent every use: some uses may fall outside copyright or be allowed by law. See [Creative Commons' AI guidance](https://creativecommons.org/cc-license-guidance/){.alert-link}.

Do not add conflicting restrictions to a standard license and present it as unchanged. The [Creative Commons FAQ](https://creativecommons.org/faq/#can-i-change-the-license-terms-or-conditions) explains why changing CC terms, including through website terms, causes confusion. Our agreements with AI providers govern their work for CoMSES. They do not change the licenses on public deposits.

### Before publication

- Check ownership and permissions for each part.
- List covered files, license names and versions, notices and required attribution.
- Check that you can redistribute the material and that dependency licenses are compatible. Ask the rights holder and a curator about unresolved questions.
- Label restricted materials clearly. A public description of a model does not give access to its files or mean that CoMSES holds or preserves them.

## Disclose material AI assistance

A short release note is enough. Describe the tool and model/version when known, when you used it, what it helped produce and how you checked the work. Mark unknowns. List AI tools here or in your methods, not as authors or contributors.

For example:

> AI assistance: [tool/model, or unknown], used [period] to revise [files] and suggest [analysis steps]. [Contributor] checked the changes by [tests, reference comparisons or other checks]. [Known limitations].

Explain the research purpose and checks for generated code, synthetic data and other outputs. Label synthetic data clearly. Routine spelling corrections and exhaustive prompt logs are unnecessary. Keep credentials, personal information and confidential prompts out of public records. A disclosure does not verify the work; you remain responsible for authorship, permissions and scientific claims.

## Request peer review

Use **Request Peer Review** on your model's detail page and follow the [review instructions](/reviews/). We plan an unchecked **“Do not use AI to assess or summarize this release during peer review”** checkbox. Once available, select it to exclude AI assessment and summarization by CoMSES and its reviewers. Human review remains available. The checkbox is not implemented yet.

Before enabling AI review, we must explain what is sent, why, to whom, what is kept and how people check results. Private release materials are limited to the stated review purpose and necessary permissions. Confidential reviewer correspondence needs separate permission. Older requests without a recorded choice do not authorize AI assistance. See our [AI policy](/about/policy/#ai-and-automation) and [privacy page](/about/data-privacy/) for details.

Publishing your release does not put it in the public domain. Others may collect public material for training or inference, including uses you may be able to challenge legally. Your review choice governs CoMSES and its reviewers, grants no training permission and cannot prevent independent collection. You keep your existing rights and legal remedies.
