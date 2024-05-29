# Support Open Science @ CoMSES Net
[![Django CI](https://github.com/comses/comses.net/actions/workflows/django-ci.yml/badge.svg)](https://github.com/comses/comses.net/actions/workflows/django-ci.yml)
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-7-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

CoMSES Net is an open, international community of researchers, educators and professionals with the common goal of improving the way we develop, document, share, and (re)use computational models in the social and ecological sciences. This repository contains the codebase for the comses.net CMS and Model Library, built with [Wagtail](https://github.com/wagtail/wagtail), [Django Rest Framework](https://www.django-rest-framework.org/), and [VueJS](https://vuejs.org/).

## Computational Model Library
The Computational Model Library maintains distinct submission information packages (SIPs) and archival information packages (AIPs) using [bagit](https://github.com/LibraryOfCongress/bagit-python), and emits [structured, standardized metadata](https://github.com/codemeta/codemeta) on every model landing page. All computational models offer citations that adhere to the guidelines and practices set forth by the [Force 11 Software Citation Working Group](https://www.force11.org/group/software-citation-working-group). Models can also undergo [peer review](https://www.comses.net/reviews/) to receive a DOI and [open code badge](https://www.comses.net/resources/open-code-badge/).

## Code of Conduct
Members who participate in this project agree to abide by the [CoMSES Net Code of Conduct](https://github.com/comses/comses.net/blob/main/CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [editors@comses.net](mailto:editors@comses.net).

## Ways to Contribute to CoMSES Net

Members are encouraged to participate and we welcome contributions of all kinds to our collective effort. Here's how you can contribute:

### Publish your Model Source Code

We develop and maintain the CoMSES Model Library, a digital repository for publishing model code that supports discovery and the [FAIR Principles for Research Software](https://doi.org/10.15497/RDA00068), software citation, reproducibility and reuse.

Publish your model here: [https://www.comses.net/codebases/](https://www.comses.net/codebases/)

### Peer Reviews

The [CoMSES Net Peer Review Process](https://www.comses.net/reviews/) helps to verify that a computational model's source code and documentation meets [baseline community standards](https://www.comses.net/resources/guides-to-good-practice/) from the software engineering and scientific communities that we serve.

Peer reviewers follow a simple checklist and inspect model code and documentation for completeness, cleanliness, and the ability to run the computational model without errors.

We're always looking for new members willing to review computational models. Feel free to submit your own computational models for peer review as well - after they pass peer review they will be eligible to be issued a DOI. 

### Lead and Organize Community Activities on Our Forums

Members of our community also use [the CoMSES Net Discourse Forums](https://forum.comses.net/) to discuss models, events, jobs, ask questions, and more. If you'd like to lead a journal club or model club or coordinate any other activities on these forums, please [**contact us**](https://www.comses.net/about/contact/).

### Update Event and Job Boards

All registered CoMSES Net members can post information about upcoming conferences, workshops and job openings on our events and jobs boards. If you would like to spread the word for new job opportunities or events, please feel free to register on our site and post it on our site!

Events board: [https://www.comses.net/events/](https://www.comses.net/events/)

Jobs board: [https://www.comses.net/jobs/](https://www.comses.net/jobs/)

### Usability Testing

CoMSES Net is actively working with the [Science Gateways Community Institute](https://sciencegateways.org) to improve the usability of our services. Please [let us know](https://comses.net/about/contact/) if you'd like to participate in upcoming usability studies, or help us conduct usability studies in your institution or area. If you encounter any usability issues while using CoMSES Net we'd love to hear your feedback too! You can use the GitHub issues here or send us a private note through the contact form.

### Development 

#### Technology Stack

```
Javascript: VueJS, typescript

Python: Django Rest Framework, Wagtail

Linux, PostgreSQL, Redis, Elasticsearch, Docker
```

Pull requests, issues to request new features, enhancements, or bug reports are all welcome. Please make sure to review the [CONTRIBUTING.md](CONTRIBUTING.md) guidelines.

[Create a pull request from a fork](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork)

[Create an issue](https://docs.github.com/en/github/managing-your-work-on-github/creating-an-issue)

#### Development Environment Setup

For more detailed development environment instructions, refer to the [CoMSES Developer Guide](https://github.com/comses/infra/wiki/Developer-Guide).

Dependencies
-------------
1. [Install Docker](https://docs.docker.com/engine/install/) ([Ubuntu-specific install instructions](https://docs.docker.com/desktop/install/ubuntu/))
2. The new `docker-compose-plugin` (e.g., `$ apt install -y docker-compose-plugin`) provides a `docker compose ...` command that replaces old `docker-compose ...` invocations
3. Create or update the file `/etc/sysctl.d/99-docker.conf` and add a line `vm.max_map_count=262144` so [elasticsearch can run properly](https://www.elastic.co/guide/en/elasticsearch/reference/current/vm-max-map-count.html). You can create / access the file with any plaintext editor like nano e.g., `$ sudo nano /etc/sysctl.d/99-docker.conf` - follow the in-terminal nano instructions to save and exit.

#### Apple Silicon + Docker workarounds

For M1/M2 chipsets you must have `export DOCKER_DEFAULT_PLATFORM=linux/amd64` set to properly build the Docker images from the command-line. Place this environment variable setting in a shell startup file e.g., `.bashrc` | `.profile` | `.zshrc` | `.zprofile` so that it will be automatically set when you open an interactive CLI shell to initiate a Docker build.

Building and installing from a fresh clone of the repository can be done by:

1. `$ make build`
2. Edit the generated `config.mk` file and set `BORG_REPO_URL` to the URL of a borg backup with preserved comses.net
   gateway content (WIP)
3. `$ make restore`

### Debugging

Enabling debugging requires custom workarounds to make the Docker environment accessible to your local system and IDEs. Visual Studio Code has a container environment that can be useful: https://code.visualstudio.com/docs/remote/containers

You can also install project dependencies into your local system. Maintaining isolation with [Python](https://docs.python.org/3/library/venv.html) and [JavaScript](https://pypi.org/project/nodeenv/) virtual environments is **strongly recommended**.    


### Other CoMSES Projects

- [Catalog](https://github.com/comses/catalog) provides web services for annotating and managing publications that reference computational research objects. Developed by CoMSES Net to assess the state of open and reusable scientific computation in agent based modeling, it depends on the [citation](https://github.com/comses/citation) Django app for bibliometric metadata management. A paper with the key findings is available at [Environmental Modelling & Software: On code sharing and model documentation of published individual and agent-based models](https://doi.org/10.1016/j.envsoft.2020.104873).
- The [Open Modeling Foundation (OMF)](https://openmodelingfoundation.github.io/) is an alliance of modeling organizations that coordinates and administers a common, community developed body of standards and best practices among diverse communities of modeling scientists. This repository hosts a [hugo site](https://gohugo.io/) and is used to collaboratively draft computational modeling standards for the OMF.
- Open training modules, educational outreach initiatives, and example FAIR+ computational models that can be run on the [Open Science Grid](https://opensciencegrid.org/) are being developed at https://github.com/comses-education


## Contributors ✨
This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of all kinds are welcome!

Contributors ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/cpritcha"><img src="https://avatars0.githubusercontent.com/u/4530298?v=4?s=100" width="100px;" alt="cpritcha"/><br /><sub><b>cpritcha</b></sub></a><br /><a href="https://github.com/comses/comses.net/commits?author=cpritcha" title="Code">💻</a> <a href="https://github.com/comses/comses.net/commits?author=cpritcha" title="Documentation">📖</a> <a href="https://github.com/comses/comses.net/issues?q=author%3Acpritcha" title="Bug reports">🐛</a> <a href="#maintenance-cpritcha" title="Maintenance">🚧</a> <a href="https://github.com/comses/comses.net/commits?author=cpritcha" title="Tests">⚠️</a> <a href="https://github.com/comses/comses.net/pulls?q=is%3Apr+reviewed-by%3Acpritcha" title="Reviewed Pull Requests">👀</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.linkedin.com/in/chrstngyn/"><img src="https://avatars0.githubusercontent.com/u/8737685?v=4?s=100" width="100px;" alt="Christine Nguyễn"/><br /><sub><b>Christine Nguyễn</b></sub></a><br /><a href="https://github.com/comses/comses.net/issues?q=author%3Achrstngyn" title="Bug reports">🐛</a> <a href="https://github.com/comses/comses.net/commits?author=chrstngyn" title="Code">💻</a> <a href="https://github.com/comses/comses.net/commits?author=chrstngyn" title="Documentation">📖</a> <a href="#design-chrstngyn" title="Design">🎨</a> <a href="https://github.com/comses/comses.net/commits?author=chrstngyn" title="Tests">⚠️</a> <a href="#maintenance-chrstngyn" title="Maintenance">🚧</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/katrinleinweber"><img src="https://avatars2.githubusercontent.com/u/9948149?v=4?s=100" width="100px;" alt="Katrin Leinweber"/><br /><sub><b>Katrin Leinweber</b></sub></a><br /><a href="https://github.com/comses/comses.net/commits?author=katrinleinweber" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://complexity.asu.edu"><img src="https://avatars0.githubusercontent.com/u/22534?v=4?s=100" width="100px;" alt="A Lee"/><br /><sub><b>A Lee</b></sub></a><br /><a href="https://github.com/comses/comses.net/issues?q=author%3Aalee" title="Bug reports">🐛</a> <a href="https://github.com/comses/comses.net/commits?author=alee" title="Code">💻</a> <a href="https://github.com/comses/comses.net/commits?author=alee" title="Documentation">📖</a> <a href="#fundingFinding-alee" title="Funding Finding">🔍</a> <a href="#ideas-alee" title="Ideas, Planning, & Feedback">🤔</a> <a href="#infra-alee" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#maintenance-alee" title="Maintenance">🚧</a> <a href="#projectManagement-alee" title="Project Management">📆</a> <a href="https://github.com/comses/comses.net/pulls?q=is%3Apr+reviewed-by%3Aalee" title="Reviewed Pull Requests">👀</a> <a href="#security-alee" title="Security">🛡️</a> <a href="https://github.com/comses/comses.net/commits?author=alee" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sgfost"><img src="https://avatars.githubusercontent.com/u/46429375?v=4?s=100" width="100px;" alt="sgfost"/><br /><sub><b>sgfost</b></sub></a><br /><a href="https://github.com/comses/comses.net/commits?author=sgfost" title="Code">💻</a> <a href="#design-sgfost" title="Design">🎨</a> <a href="https://github.com/comses/comses.net/commits?author=sgfost" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/BlllueSea"><img src="https://avatars.githubusercontent.com/u/20047708?v=4?s=100" width="100px;" alt="BlllueSea"/><br /><sub><b>BlllueSea</b></sub></a><br /><a href="https://github.com/comses/comses.net/commits?author=BlllueSea" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/CharlesSheelam"><img src="https://avatars.githubusercontent.com/u/100802119?v=4?s=100" width="100px;" alt="Charles Sheelam"/><br /><sub><b>Charles Sheelam</b></sub></a><br /><a href="https://github.com/comses/comses.net/commits?author=CharlesSheelam" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/hwelsters"><img src="https://avatars.githubusercontent.com/u/84760072?v=4?s=100" width="100px;" alt="hwelsters"/><br /><sub><b>hwelsters</b></sub></a><br /><a href="https://github.com/comses/comses.net/commits?author=hwelsters" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Krisha100"><img src="https://avatars.githubusercontent.com/u/57967961?v=4?s=100" width="100px;" alt="Krisha Vekaria"/><br /><sub><b>Krisha Vekaria</b></sub></a><br /><a href="https://github.com/comses/comses.net/commits?author=Krisha100" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->
