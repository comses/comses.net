# Support Open Science @ CoMSES Net
[![Build Status](https://travis-ci.com/comses/comses.net.svg?branch=master)](https://travis-ci.com/comses/comses.net)
[![Coverage Status](https://coveralls.io/repos/github/comses/comses.net/badge.svg?branch=master)](https://coveralls.io/github/comses/comses.net?branch=master)
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-4-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

CoMSES Net is an open, international community of researchers, educators and professionals with the common goal of improving the way we develop, document, share, and (re)use computational models in the social and ecological sciences. This repository contains the codebase for the comses.net CMS and Model Library, built with [Wagtail](https://github.com/wagtail/wagtail), [Django Rest Framework](https://www.django-rest-framework.org/), and [VueJS](https://vuejs.org/).

## Computational Model Library
The Computational Model Library maintains distinct submission information packages (SIPs) and archival information packages (AIPs) using [bagit](https://github.com/LibraryOfCongress/bagit-python), and emits [structured, standardized metadata](https://github.com/codemeta/codemeta) on every model landing page. All computational models offer citations that adhere to the guidelines and practices set forth by the [Force 11 Software Citation Working Group](https://www.force11.org/group/software-citation-working-group). Models can also undergo [peer review](https://www.comses.net/reviews/) to receive a DOI and [open code badge](https://www.comses.net/resources/open-code-badge/). Major updates to these processes are anticipated in 2021 - stay tuned!

Developer setup instructions:
-------------
Run `./build.sh` to build the Docker image, generate secrets, and a symlinked `docker-compose.yml` file. Run `docker-compose up -d` to start all containers. 

The `build.sh` script relies on
[envsubst](https://www.gnu.org/software/gettext/manual/html_node/envsubst-Invocation.html) - to install this properly on
OS X you may need to install [macports](https://www.macports.org/) or use [homebrew](https://brew.sh/) and `brew install
gettext`.

@cpritcha has created an experimental debug setup lives in the `deploy/debug` folder. Files in the debug will need to be brought to this directory to work and the settings file will have to be switched to the debug settings file (please describe this more fully at some point @cpritcha).


## Import metadata and codebases
Extract JSON data files from https://github.com/comses/docker-openabm and place them in a directory accessible to the `cms` container along with a `models/` directory pulled from the `openabm-files` root. Then run `docker-compose exec cms bash` to enter the `cms` container and run `invoke import_all` to migrate the Drupal data into Django and copy the model library filesystem data into the new archival repository format.

## Contributors ✨
This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind are welcome!

Contributors ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://github.com/cpritcha"><img src="https://avatars0.githubusercontent.com/u/4530298?v=4" width="100px;" alt=""/><br /><sub><b>cpritcha</b></sub></a><br /><a href="https://github.com/comses/comses.net/commits?author=cpritcha" title="Code">💻</a> <a href="https://github.com/comses/comses.net/commits?author=cpritcha" title="Documentation">📖</a> <a href="https://github.com/comses/comses.net/issues?q=author%3Acpritcha" title="Bug reports">🐛</a> <a href="#maintenance-cpritcha" title="Maintenance">🚧</a> <a href="https://github.com/comses/comses.net/commits?author=cpritcha" title="Tests">⚠️</a> <a href="https://github.com/comses/comses.net/pulls?q=is%3Apr+reviewed-by%3Acpritcha" title="Reviewed Pull Requests">👀</a></td>
    <td align="center"><a href="https://www.linkedin.com/in/chrstngyn/"><img src="https://avatars0.githubusercontent.com/u/8737685?v=4" width="100px;" alt=""/><br /><sub><b>Christine Nguyễn</b></sub></a><br /><a href="https://github.com/comses/comses.net/issues?q=author%3Achrstngyn" title="Bug reports">🐛</a> <a href="https://github.com/comses/comses.net/commits?author=chrstngyn" title="Code">💻</a> <a href="https://github.com/comses/comses.net/commits?author=chrstngyn" title="Documentation">📖</a> <a href="#design-chrstngyn" title="Design">🎨</a> <a href="https://github.com/comses/comses.net/commits?author=chrstngyn" title="Tests">⚠️</a> <a href="#maintenance-chrstngyn" title="Maintenance">🚧</a></td>
    <td align="center"><a href="https://github.com/katrinleinweber"><img src="https://avatars2.githubusercontent.com/u/9948149?v=4" width="100px;" alt=""/><br /><sub><b>Katrin Leinweber</b></sub></a><br /><a href="https://github.com/comses/comses.net/commits?author=katrinleinweber" title="Code">💻</a></td>
    <td align="center"><a href="https://complexity.asu.edu"><img src="https://avatars0.githubusercontent.com/u/22534?v=4" width="100px;" alt=""/><br /><sub><b>A Lee</b></sub></a><br /><a href="https://github.com/comses/comses.net/issues?q=author%3Aalee" title="Bug reports">🐛</a> <a href="https://github.com/comses/comses.net/commits?author=alee" title="Code">💻</a> <a href="https://github.com/comses/comses.net/commits?author=alee" title="Documentation">📖</a> <a href="#fundingFinding-alee" title="Funding Finding">🔍</a> <a href="#ideas-alee" title="Ideas, Planning, & Feedback">🤔</a> <a href="#infra-alee" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#maintenance-alee" title="Maintenance">🚧</a> <a href="#projectManagement-alee" title="Project Management">📆</a> <a href="https://github.com/comses/comses.net/pulls?q=is%3Apr+reviewed-by%3Aalee" title="Reviewed Pull Requests">👀</a> <a href="#security-alee" title="Security">🛡️</a> <a href="https://github.com/comses/comses.net/commits?author=alee" title="Tests">⚠️</a></td>
  </tr>
</table>

<!-- markdownlint-enable -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

## How to Contribute

CoMSES Net is dedicated to fostering open and reproducible scientific computation through cyberinfrastructure and community development. Our mission is to improve the way we develop, document, and share our computational models so we can build on each other’s work more effectively and model our way to a better global future. 

Members are encouraged to participate in our collective effort to expand and strengthen CoMSES Net at all levels. The following information details ways in which members can contribute which include include code contributions, curating resources for our community, and more. 

Thanks for being a part of CoMSES Net! 

### Code of Conduct
This project and participating members is governed by the [Code of Conduct](https://github.com/openmodelingfoundation/openmodelingfoundation.github.io/blob/develop/CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [editors@comses.net](mailto:editors@comses.net).

### Archive your Model Source Code

We develop and maintain the CoMSES Model Library, a digital repository to archive model code that supports discovery and the FAIR Data Principles for software citation, reproducibility and reuse.

Archive your model here: [https://www.comses.net/codebases/](https://www.comses.net/codebases/)

### Usability Testing

Through usability testing, we can identify design flaws and find solutions to better serve our CoMSES Net community. To improve our website and tools, we are always looking for members to participate in our usability tests so we can:

- diagnose usability problems
- collect qualitative and quantitative data
- determine a participant's satisfaction with our tools

If you are interested in participating in usability tests, please email us at [editors@comses.net](mailto:editors@comses.net).

### Active Development

Our technology stack includes:

```
Javascript: VueJS, webpack, typescript

Python: Django Rest Framework, Wagtail

MySQL / PostgreSQL

Linux

Docker
```

Members are encouraged to contribute to our repositories by creating a pull request (PR) from a bug or reporting bugs by creating issues in a repository.

[Creating a pull request from a fork](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork)

[Creating an issue](https://docs.github.com/en/github/managing-your-work-on-github/creating-an-issue)

**Repositories members can contribute to:**

- [Catalog](https://github.com/comses/catalog)
- [Citation](https://github.com/comses/citation)
- [Open Modeling Foundation (OMF)](https://github.com/openmodelingfoundation/openmodelingfoundation.github.io)

### Manage Peer Reviews

During a peer review, model code is inspected to identify possible improvements and ensure that requirements are met for software citation, reproducibility and reuse. 

If you are interested in managing peer reviews, please email us at [editors@comses.net](mailto:editors@comses.net).

### Lead and Organize Community Activities on Our Forums

Members of our community use [CoMSES Net Discourse Forums](https://forum.comses.net/) to discuss models, curate events, and more. By posting and engaging on our forums, members can collectively curate better resources for the CoMSES Community.

### Update Event and Job Boards

We want to keep our community updated on current events and available academic and industry positions relevant to the CoMSES Net Community. Any registered CoMSES Net members can post information about upcoming conferences, workshops and available positions.

Events board: [https://www.comses.net/events/](https://www.comses.net/events/)

Jobs board: [https://www.comses.net/jobs/](https://www.comses.net/jobs/)
