[TOC]

# Introduction

This tutorial introduces emerging practices and community standards for developing and publishing [FAIR](#the-fair-principles) computational models. This will help your research be more transparent, interoperable, reusable, and increase its longevity and impact.

![Watch the Introduction](https://www.youtube.com/watch?v=Am3aNtXQWec)

# The FAIR Principles

!!! info ""
    The FAIR principles are a set of guidelines to make digital assets more **Findable**, **Accessible**, **Interoperable** and **Reusable** - in our case, the digital assets are computational models that examine social-ecological systems. The principles were initially published in 2016 and aimed generally at scientific data: CSVs, shapefiles, Excel sheets, relational databases, graph databases, etc. These FAIR data principles were later refined with additional guidance for Research Software by a Research Data Alliance working group and published as the FAIR for Research Software Principles in 2022.

![Watch the FAIR Principles Video](https://www.youtube.com/watch?v=cQz6_c6VsKo)

#### Publications about the FAIR Principles

[FAIR Guiding Principles for scientific data management and stewardship (2016)](https://doi.org/10.1038/sdata.2016.18)
Wilkinson, M. D., Dumontier, M., Aalbersberg, I. J., Appleton, G., Axton, M., Baak, A., ... & Mons, B. (2016). The FAIR Guiding Principles for scientific data management and stewardship. Scientific data, 3(1), 1-9. https://doi.org/10.1038/sdata.2016.18

[FAIR Principles for Research Software (2022)](https://doi.org/10.15497/RDA00068)
Chue Hong, Neil P., Katz, Daniel S., Barker, Michelle, Lamprecht, Anna-Lena, Martinez, Carlos, Psomopoulos, Fotis E., Harrow, Jen, Castro, Leyla Jael, Gruenpeter, Morane, Martinez, Paula Andrea, Honeyman, Tom, Struck, Alexander, Lee, Allen, Loewe, Axel, van Werkhoven, Ben, Jones, Catherine, Garijo, Daniel, Plomp, Esther, Genova, Francoise, … RDA FAIR4RS WG. (2022). FAIR Principles for Research Software (FAIR4RS Principles) (1.0). https://doi.org/10.15497/RDA00068

# Metadata

!!! info ""
    Metadata, **data about data**, a collection of data that describes some *other data*. In this case, our *other data* is a computational model, and the metadata are the descriptive fields, structured data, narrative prose text, etc., the **human and machine-readable things** we use to annotate our computational models so others can more easily Find, Evaluate, or Reuse them. Some examples of metadata: keywords, contributors, sponsors, a durable graph of provenance, the semantic version for a specific snapshot of code, an abstract or description, links and permanent identifiers to related resources and references, links and permanent identifiers to semantic ontologies that provide rigorous details on a computational model's inputs and outputs


![Watch the Video on Metadata](https://www.youtube.com/watch?v=UaWwHv5O2Pc)

#### Software metadata resources and links

!!! info ""
    GitHub [now supports](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files) software citation via [CITATION.cff files](https://citation-file-format.github.io/). CITATION.cff files are plain old YAML files that follow a schema which supports good software citation practices.


- [OntoSoft: A distributed semantic registry for scientific software](https://ieeexplore.ieee.org/document/7870916)
- [CodeMeta: A minimal metadata schema for science software and code in JSON and XML](https://codemeta.github.io/)

# Code Management

![Watch the Video on Code Management](https://www.youtube.com/watch?v=ozZJEGNuwz8)

# Archiving

![Watch the Video on Archiving Your Code](https://www.youtube.com/watch?v=uodCLUADYE4)

# Documentation

![Watch the Video on Model Documentation](https://www.youtube.com/watch?v=iN6iBwaHR68)

#### More information on the ODD protocol

[A standard protocol for describing individual-based and agent-based models](https://doi.org/10.1016/j.ecolmodel.2006.04.023)
Grimm, V., Berger, U., Bastiansen, F., Eliassen, S., Ginot, V., Giske, J., Goss-Custard, J., Grand, T., Heinz, S., Huse, G., Huth, A., Jepsen, J. U., Jørgensen, C., Mooij, W. M., Müller, B., Pe'er, G., Piou, C., Railsback, S. F., Robbins, A. M., Robbins, M. M., Rossmanith, E., Rüger, N., Strand, E., Souissi, S., Stillman, R. A., Vabø, R., Visser, U., & DeAngelis, D. L. (2006). A standard protocol for describing individual-based and agent-based models. Ecological Modelling, 198, 115-126. https://doi.org/10.1016/j.ecolmodel.2006.04.023

[The ODD Protocol for Describing Agent-Based and Other Simulation Models: A Second Update to Improve Clarity, Replication, and Structural Realism](http://jasss.soc.surrey.ac.uk/23/2/7.html)
Grimm, V., S.F. Railsback, C.E. Vincenot, U. Berger, C. Gallagher, D.L. DeAngelis, B. Edmonds, J. Ge, J. Giske, J. Groeneveld, A.S.A. Johnston, A. Milles, J. Nabe-Nielsen, J. Gareth Polhill, V. Radchuk, M.-S. Rohwäder, R.A. Stillman, J.C. Thiele, and D. Ayllón (2020) The ODD Protocol for Describing Agent-Based and Other Simulation Models: A Second Update to Improve Clarity, Replication, and Structural Realism, Journal of Artificial Societies and Social Simulation 23(2) 7, Doi: 10.18564/jasss.4259 Url: http://jasss.soc.surrey.ac.uk/23/2/7.html

# Licenses

!!! info ""
    Our general recommendation is to use the [MIT License](https://spdx.org/licenses/MIT.html) for an easy to understand, permissive license that supports maximal reuse with a protective liability clause.

Please also note that the [Creative Commons does NOT recommend using their licenses for software](https://creativecommons.org/faq/#can-i-apply-a-creative-commons-license-to-software).


![Watch the Video on Software Licenses](https://www.youtube.com/watch?v=-OMLPF8ZFf4)

#### Additional guidance on choosing an open source license

- [opensource.guide recommendations for OSS licensing](https://opensource.guide/legal/#which-open-source-license-is-appropriate-for-my-project)
- [choosealicense.com](https://choosealicense.com/) by [GitHub](https://github.com/)
- [UK Software Sustainability Institute's Guide to Choosing an Open Source License](https://www.software.ac.uk/resources/guides/choosing-open-source-licence)
- [Public License Selector](https://ufal.github.io/public-license-selector/) from the [Institute of Formal and Applied Linguistics](https://ufal.mff.cuni.cz/)
- [How to Choose the Right Open Source License](https://fossa.com/blog/how-choose-right-open-source-license/) by [FOSSA](https://fossa.com/)
- [GNU License Recommendations](https://www.gnu.org/licenses/license-recommendations.en.html) from the [Free Software Foundation](https://www.fsf.org/)

# Final Assessment

Once you have finished the above modules, please complete the following assessment. You will receive a certificate of completion and digital badge after successfully passing the assessment.

[Complete the final assessment](https://forms.gle/5WjshdE2QXXpRhRh9)

# Feedback

Please use our [education forums](https://forum.comses.net/c/education) to ask questions or provide feedback on this course. Thanks!
