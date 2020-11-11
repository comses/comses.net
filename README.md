# Support Open Science @ CoMSES Net
[![Build Status](https://travis-ci.org/comses/comses.net.svg?branch=master)](https://travis-ci.org/comses/comses.net)
[![Coverage Status](https://coveralls.io/repos/github/comses/comses.net/badge.svg?branch=master)](https://coveralls.io/github/comses/comses.net?branch=master)

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
