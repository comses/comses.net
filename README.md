# Computational Reproducibility @ CoMSES Net
[![Build Status](https://travis-ci.org/comses/core.comses.net.svg?branch=master)](https://travis-ci.org/comses/core.comses.net)
[![Coverage Status](https://coveralls.io/repos/github/comses/core.comses.net/badge.svg?branch=master)](https://coveralls.io/github/comses/core.comses.net?branch=master)

A revamped version of the openabm.org CMS using Wagtail, Django Rest Framework, Git, and VueJS.

## Computational Model Library Version 2 (this time with greater reproducibility)
Improvements to the computational model library are in-progress, with archived computational models versioned in git, packaged with [bagit](https://github.com/LibraryOfCongress/bagit-python), described with [standardized metadata](https://github.com/codemeta/codemeta) and citable with citations adhering to the guidelines and practices set forth by the [Force 11 Software Citation Working Group](https://www.force11.org/group/software-citation-working-group). 

Developer build instructions:
-------------
Run `bash build.sh` to build the Docker image, generate secrets, and a symlinked `docker-compose.yml` file. Then run `docker-compose up`. 

A debug setup exists in the `deploy/debug` folder. Files in the debug will need to be brough to this directory to work and the settings file will have to switched to the debug settings file.

## Documentation (for developers and editors)

See [here](http://comsesnet.readthedocs.io/en/latest/)



## Import metadata and codebases
Extract JSON data files from https://github.com/comses/docker-openabm and place them in a directory accessible to the `cms` container along with a `models/` directory pulled from the `openabm-files` root. Then run `docker-compose exec cms bash` to enter the `cms` container and run `invoke import_all` to migrate the Drupal data into Django and copy the model library filesystem data into the new archival repository format.
