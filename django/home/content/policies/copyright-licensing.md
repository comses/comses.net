> Draft for community and governance review. This document has not been adopted.

## Rights and permissions

Proposed expectations: contributors must hold the rights or permissions needed to submit their materials and grant the permissions required by the approved Terms. Credit all contributors and identify third-party components. Do not assume that publicly accessible code or data is free of copyright or other restrictions.

## License each kind of material clearly

Identify the license for model source code, custom scripts, documentation, and included data. Preserve required copyright notices and attribution. Explain when components have different licenses and check that redistribution is permitted. Linked datasets retain their own licenses and access conditions.

Choose licenses that enable reuse where the rights holder permits it. Record the files covered by each license in a README or license inventory; do not assign one license to an entire deposit by default. A software license does not automatically license a paper, dataset, or community post. Preserve third-party licenses and notices. If ownership, permission or compatibility is unclear, ask the rights holder and a human curator before distributing the affected material.

## Choosing licenses

Proposed default: model code and custom scripts should use an OSI-approved software license. Restricted licenses may be accepted through a documented exception, with the reason, restrictions and consequences for reuse visible on the public record. Ordinary exception approval authority and criteria must be defined before adoption. An exception does not make a restricted license open source or supply missing rights to distribute the material.

Contributors may appeal a licensing-exception refusal or request a departure from the ordinary exception criteria to the CoMSES Executive Board. The appeal should explain the scientific or preservation value, why the ordinary criteria cannot be met, and the resulting limits on inspection, execution, modification and redistribution. A Board-approved departure must record the decision, rationale, applicable conditions and implications for reuse on the public record while protecting confidential details. Board approval cannot supply missing rights or waive applicable law. Define the appeal submission and decision process before adoption.

An approved exception may permit a public metadata record for a model whose files require additional permission to access or reuse. Publish only metadata CoMSES is authorized to disclose, identify the model version and rights holder where known, and explain the restrictions and how to request access or permission. License the metadata separately from the model materials. Public metadata does not grant access to the files, authorize CoMSES to host them, or change their license. Cases outside the ordinary exception criteria may follow the Executive Board appeal route above.

The following are contributor recommendations, not automatic assignments or an exhaustive license list. Use established, unmodified licenses and check obligations from employers, funders, collaborators and dependencies before choosing.

| Material | Suggested starting point | What to consider |
| --- | --- | --- |
| Model code and custom scripts | [MIT](https://opensource.org/license/mit) for a short permissive license, or [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) for permissive reuse with an express patent grant and related conditions. | Both allow commercial reuse. Preserve notices and check dependency compatibility. Consider [GPL-3.0](https://opensource.org/license/gpl-3.0) if you want copyleft obligations when covered software is distributed; review how it applies to your combined work. |
| Datasets | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en) when authorized to waive copyright and database rights, or [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en) when attribution should be a license condition. | Check rights in both the database and its contents. Neither choice supplies missing third-party permissions or clears privacy, confidentiality or access restrictions. Credit data sources even where attribution is a community expectation rather than a license requirement. |
| Narrative documentation, figures and tutorials | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en) for reuse and adaptation with attribution. | Identify separately licensed images, quotations, articles and embedded code examples. Keep code examples under a suitable software license where appropriate. |

Under the [OSI Open Source Definition](https://opensource.org/osd), an open-source software license cannot prohibit commercial use or a field of use such as AI training. Describe software with such restrictions accurately as restricted or source-available, as appropriate. A NonCommercial Creative Commons license is not an open-source software license. Restricted materials require the documented exception described above.

## AI reuse and the limits of licensing

Licenses communicate permissions within the rights they cover. They may not control every AI use: fair use, fair dealing, text-and-data-mining exceptions or uses outside copyright can apply depending on jurisdiction and circumstances. A restrictive license or a "no AI training" notice does not guarantee exclusion from training. See [Creative Commons' current AI licensing guidance](https://creativecommons.org/cc-license-guidance/).

Do not append a training ban or other conflicting restriction to a standard open license while continuing to describe it as that unmodified license. The [Creative Commons FAQ](https://creativecommons.org/faq/#can-i-change-the-license-terms-or-conditions) explains the problems with altering CC licenses, including through website terms. CoMSES community preferences and agreements with its own inference providers are separate from the permissions a public deposit already grants; see the [AI policy](/about/policy/ai-automated-processing/#provider-commitments).

## License selection checklist

- Identify the rights holders, including any employer or institution, and obtain needed permissions.
- Separate code, data, documentation and third-party materials; list the files each license covers.
- Choose an established license for each part using the recommendations above, and check compatibility and redistribution conditions.
- Preserve license texts, notices, attribution, source links and any limits on access. Refer unclear ownership or third-party permissions to a human curator and the rights holder.
- Confirm that any "open source" label matches the license. Describe AI preferences separately, and understand that licenses may not govern every AI use.
- Include the license inventory with the release and check it before publication. This draft does not relicense existing published releases.

## Reuse and citation

Users should follow the license attached to the specific release or component and cite the version used. Citation and attribution serve related but distinct purposes; citation alone does not replace compliance with license conditions. AI-generated or transformed material still requires provenance and rights review; see the [AI policy](/about/policy/ai-automated-processing/).

## Rights concerns and unresolved choices

Send rights concerns to the [CoMSES team](/about/contact/), identifying the material, the claimed rights, and enough information to assess the concern. Do not publish sensitive supporting evidence. A formal notice, response, and reconsideration procedure must be approved before adoption.

The approved policy must also specify any default license for site-authored text and metadata, acceptable submission licenses, and the operator's preservation permissions. This draft assigns no new license to existing deposits or metadata.
