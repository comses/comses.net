# Support Open Science @ CoMSES Net
[![Build Status](https://travis-ci.com/comses/comses.net.svg?branch=master)](https://travis-ci.com/comses/comses.net)
[![Coverage Status](https://coveralls.io/repos/github/comses/comses.net/badge.svg?branch=master)](https://coveralls.io/github/comses/comses.net?branch=master)
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-4-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

CoMSES Net is an open, international community of researchers, educators and professionals with the common goal of improving the way we develop, document, share, and (re)use computational models in the social and ecological sciences. This repository contains the codebase for the comses.net CMS and Model Library, built with [Wagtail](https://github.com/wagtail/wagtail), [Django Rest Framework](https://www.django-rest-framework.org/), and [VueJS](https://vuejs.org/).

## Computational Model Library
The Computational Model Library maintains distinct submission information packages (SIPs) and archival information packages (AIPs) using [bagit](https://github.com/LibraryOfCongress/bagit-python), and emits [structured, standardized metadata](https://github.com/codemeta/codemeta) on every model landing page. All computational models offer citations that adhere to the guidelines and practices set forth by the [Force 11 Software Citation Working Group](https://www.force11.org/group/software-citation-working-group). Models can also undergo [peer review](https://www.comses.net/reviews/) to receive a DOI and [open code badge](https://www.comses.net/resources/open-code-badge/). Updates to these processes are anticipated in 2021 - stay tuned!

## Code of Conduct
Members who participate in this project agree to abide by the [CoMSES Net Code of Conduct](https://github.com/comses/comses.net/blob/main/CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [editors@comses.net](mailto:editors@comses.net).

## Ways to Contribute to CoMSES Net

Members are encouraged to participate and we welcome contributions of all kinds to our collective effort. Here's how you can contribute:

### Archive your Model Source Code

We develop and maintain the CoMSES Model Library, a digital repository to archive model code that supports discovery and the FAIR Data Principles for software citation, reproducibility and reuse.

Archive your model here: [https://www.comses.net/codebases/](https://www.comses.net/codebases/)

### Usability Testing

Usability testing helps our science gateway better serve its community, and CoMSES Net is actively working with the [Science Gateways Community Institute](https://sciencegateways.org) to improve the usability of our services. Please [let us know](https://comses.net/about/contact/) if you'd like to participate in upcoming usability studies or help us conduct usability studies in your institution or area.

### Active Development

Our technology stack includes:

```
Javascript: VueJS, webpack, typescript

Python: Django Rest Framework, Wagtail

PostgreSQL / MySQL

Linux

Docker
```

We accept contributions of all kinds! Pull requests, issues to request new features, enhancements, or bug reports are all welcome. Please make sure to review the [CONTRIBUTING.md](CONTRIBUTING.md) guidelines.

[Create a pull request from a fork](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork)

[Create an issue](https://docs.github.com/en/github/managing-your-work-on-github/creating-an-issue)

Developer setup instructions:
-------------
Run `./build.sh` to build the Docker image and generate secrets and a symlinked `docker-compose.yml` file. Run `docker-compose up -d` to start all containers. 

The `build.sh` script relies on
[envsubst](https://www.gnu.org/software/gettext/manual/html_node/envsubst-Invocation.html) and to install this on macOS you may need to install [macports](https://www.macports.org/) or use [homebrew](https://brew.sh/) and `brew install gettext`.

Enabling debugging is still a bit of a pain and requires custom workarounds to the Docker environment. @cpritcha should document these at some point.

**Other Repositories**

- [Catalog](https://github.com/comses/catalog) provides web services for annotating and managing publications that reference computational research objects. Developed by CoMSES Net to assess the state of open and reusable scientific computation in agent based modeling, it depends on the [citation](https://github.com/comses/citation) Django app for bibliometric metadata management. Our instance of catalog runs at https://catalog.comses.net
- The [Open Modeling Foundation (OMF)](https://github.com/openmodelingfoundation/openmodelingfoundation.github.io) is an alliance of modeling organizations that coordinates and administers a common, community developed body of standards and best practices among diverse communities of modeling scientists. This repository hosts a [hugo site](https://gohugo.io/) and is used to collaboratively draft computational modeling standards for the OMF.

### Peer Reviews

The CoMSES Net Computational Model Peer Review process helps us verify that a model's source code and documentation meets baseline standards derived from [**good practices**](https://www.comses.net/resources/guides-to-good-practice/) in the software engineering and scientific communities that we serve. This process is intended to be efficient and allows us to foster higher quality models.

As a peer reviewer, you inspect model code to identify possible improvements and ensure that requirements are met for software citation, reproducibility and reuse. If you are interested in serving as a peer reviewer for model code, please [**contact us**](https://www.comses.net/about/contact/).

To learn more about peer reviews, please visit [**CoMSES Net Computational Library Peer Review**](https://www.comses.net/reviews/).

### Lead and Organize Community Activities on Our Forums

Members of our community also use [the CoMSES Net Discourse Forums](https://forum.comses.net/) to discuss models, events, jobs, ask questions, and more. If you'd like to lead a journal club or model club or coordinate any other activities on these forums, please [**contact us**](https://www.comses.net/about/contact/).

### Update Event and Job Boards

Part of our mission to continue serving our community is to keep them updated on relevant events and jobs. All registered CoMSES Net members can post information about upcoming conferences, workshops and job openings on our events and jobs boards.

Events board: [https://www.comses.net/events/](https://www.comses.net/events/)

Jobs board: [https://www.comses.net/jobs/](https://www.comses.net/jobs/)

## Contributors ✨
This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of all kinds are welcome!

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
