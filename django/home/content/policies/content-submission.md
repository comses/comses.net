> Draft for community and governance review. This document has not been adopted.

<a id="scope"></a>

## Model library scope and supporting materials

The CoMSES Computational Model Library accepts computational models together with their model-specific dependencies and supporting materials. Our focus is on agent-based models of social and ecological systems, and we also welcome broader computational models, including geosimulation, cellular automata, and dynamic networks.

A submission should include:

- The model source code and narrative documentation explaining the model.
- Model-specific dependencies, including custom scripts used to prepare or clean data, run the model, or analyze its results.
- Permanent URLs to important input datasets and representative example output datasets.

Supporting scripts belong with the model source code so that others can understand how the model's inputs and results were produced. Datasets may remain in suitable external repositories and be connected to the model through permanent URLs.

Through an approved licensing exception, CoMSES may instead provide a public metadata record describing a model whose files require additional access or reuse permissions. Clearly label the record as metadata-only or as describing restricted materials, state which files CoMSES actually holds, and provide the applicable rights statement and access or permission route. A public record must not imply that the model files are openly available or preserved by CoMSES when they are not.

<a id="outside-scope"></a>

## Materials normally outside scope

Standalone scripts, datasets, and general-purpose software without a clear connection to a deposited computational model are normally outside the library's scope. Curators may accept exceptions as described below.

<a id="exceptions"></a>

## Curatorial discretion and transparent exceptions

Curators may accept submissions outside the usual scope when there is a clear justification. Discretion remains available, provided that the exception is transparent and clearly visible.

The affected public model record must identify the departure from the usual scope and explain why it was accepted. The explanation must be visible on the record, not available only in private correspondence or internal review notes.

If you are unsure whether a submission fits the library's scope, please [contact the CoMSES team](/about/contact/) before submitting it.

## Preparing a reusable submission

Proposed expectations: identify the model version, contributors and their roles, the associated research, and the licenses covering each part of the package. Describe the required software environment, dependency versions, installation and execution steps, parameters, random seeds where relevant, and a representative run with expected outputs. Explain known limitations and unresolved dependencies. Use an appropriate narrative documentation framework; see the [documentation guidance](/about/faq/).

Use the [license selection checklist](/about/policy/copyright-licensing/#license-selection-checklist) to choose and record licenses separately for code, datasets and documentation. Bring unclear ownership and third-party permissions to a human curator before publication. Disclose [material AI assistance](/about/policy/ai-automated-processing/#contributor-disclosure), especially consequential changes to code, data or results, with the human checks performed; exhaustive prompt logs are not required.

When requesting peer review, the proposed [AI assistance choice](/about/policy/review-publication/#ai-assistance-and-your-review-request) lets you opt out of AI assessment and summarization for that review. Publication makes a release publicly accessible without changing its license or placing it in the public domain; CoMSES cannot guarantee that third parties will not collect public materials for training or other inference.

For input and example output datasets, identify the dataset version, provenance, and access conditions alongside permanent URLs. If data cannot be shared, explain why, describe how access may be obtained, and supply a suitable synthetic or reduced example where possible. Do not include personal or restricted data without permission. Document any resulting limit on reproducibility.

## Exceptions and incomplete materials

Discretion applies to these expectations as well as scope. An accepted departure, its justification, and its effect on reuse or review must be clearly visible on the affected public record. Transparency must not disclose sensitive information: explain the limitation publicly while keeping protected details private. Discretion does not authorize infringement or disclosure without permission.

Licensing cases outside the ordinary exception criteria, including refused exception requests, may be appealed to the CoMSES Executive Board under the copyright and licensing policy. Board-approved departures must retain accurate license labels and publicly explain the limits on reuse.

See [copyright and licensing](/about/policy/copyright-licensing/) and [review and publication](/about/policy/review-publication/) for related requirements. The [publishing tutorial](https://forum.comses.net/t/publishing-your-model-1-getting-started/7377) provides submission steps.
