import contextlib
import csv
import io
import json
import logging
import os
import re
from collections import defaultdict, Iterable
from datetime import datetime
from textwrap import shorten
from typing import Dict

from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from taggit.models import Tag

from core.summarization import summarize_to_text
from home.models import Event, Job, MemberProfile, Platform, ComsesGroups, Institution
from library.models import (Contributor, Codebase, CodebaseRelease, CodebaseTag, License,
                            CodebaseContributor, OPERATING_SYSTEMS, CodebaseReleaseDownload)
from .utils import get_first_field, get_field, get_field_attributes, to_datetime

logger = logging.getLogger(__name__)

LICENSES = """id,name,url
    0,"None",""
    1,"GPL-2.0",http://www.gnu.org/licenses/gpl-2.0.html
    2,"GPL-3.0",http://www.gnu.org/licenses/gpl-3.0.html
    3,"Apache-2.0",http://www.apache.org/licenses/LICENSE-2.0.html
    4,"CC-BY-3.0",http://creativecommons.org/licenses/by/3.0/
    5,"CC-BY-SA-3.0",http://creativecommons.org/licenses/by-sa/3.0/
    6,"CC-BY-ND-3.0",http://creativecommons.org/licenses/by-nd/3.0
    7,"CC-BY-NC-3.0",http://creativecommons.org/licenses/by-nc/3.0
    8,"CC-BY-NC-SA-3.0",http://creativecommons.org/licenses/by-nc-sa/3.0
    9,"CC-BY-NC-ND-3.0",http://creativecommons.org/licenses/by-nc-nd/3.0
    10,"AFL-3.0",http://www.opensource.org/licenses/afl-3.0.php
    11,"BSD-2-Clause",http://opensource.org/licenses/BSD-2-Clause
    12,"MIT", https://opensource.org/licenses/MIT"""

PLATFORMS = """id,active,name,url,description
    0,f,other,NULL,''
    1,t,Ascape,http://ascape.sourceforge.net/,"Ascape is an innovative tool for developing and exploring general-purpose agent-based models. It is designed to be flexible and powerful, but also approachable, easy to use and expressive. Models can be developed in Ascape using far less code than in other tools. Ascape models are easier to explore, and profound changes to the models can be made with minimal code changes. Ascape offers a broad array of modeling and visualization tools."
    2,f,Breve,http://www.spiderland.org/,"breve is a free, open-source software package which makes it easy to build 3D simulations of multi-agent systems and artificial life. Using Python, or using a simple scripting language called steve, you can define the behaviors of agents in a 3D world and observe how they interact. breve includes physical simulation and collision detection so you can simulate realistic creatures, and an OpenGL display engine so you can visualize your simulated worlds."
    3,t,Cormas,http://cormas.cirad.fr/en/outil/outil.htm,"Cormas is a simulation platform based on the VisualWorks programming environment which allows the development of applications in the object-oriented programming language SmallTalk. Cormas pre-defined entities are SmallTalk generic classes from which, by specialization and refining, users can create specific entities for their own model."
    4,t,DEVS-Suite,http://acims.asu.edu/software/devs-suite/,"DEVS-Suite 3.0.0 is the first discrete-event/discrete-time simulator that offers the capability to generate and visualize Superdense Time Trajectories. Two new types of time-based trajectories (plots) are introduced to the Business Intelligence Reporting Tool (BIRT) and then integrated into the DEVS-Suite 2.1.0. This simulator supports a rich set of menu-driven capabilities to create and customize two new kinds of time-based trajectories."
    5,t,EcoLab,http://ecolab.sourceforge.net/,"EcoLab is both the name of a software package and a research project that is looking at the dynamics of evolution."
    6,t,Mason,http://cs.gmu.edu/~eclab/projects/mason/,"MASON is a fast discrete-event multiagent simulation library core in Java, designed to be the foundation for large custom-purpose Java simulations, and also to provide more than enough functionality for many lightweight simulation needs. MASON contains both a model library and an optional suite of visualization tools in 2D and 3D."
    7,f,Mass,http://mass.aitia.ai/,"A modeling platform consisting of the Functional Agent-based Language for Simulation (FABLES) programming language, a participatory simulations software, and the Model Exploration Module (MEME), which manages experiments for batch processing and analysis."
    8,f,Mobildyc,http://w3.avignon.inra.fr/mobidyc/index.php/English_summary,"Mobidyc is a software project that aims to promote Individual-Based Modelling in the field of ecology, biology and environment. It is the acronym for MOdelling Based on Individuals for the DYnamics of Communities."
    9,t,NetLogo,http://ccl.northwestern.edu/netlogo/,"NetLogo is a multi-agent programmable modeling environment. It is used by tens of thousands of students, teachers and researchers worldwide. It also powers HubNet participatory simulations. It is authored by Uri Wilensky and developed at the CCL. You can download it free of charge."
    10,t,Repast,http://repast.github.io,"The Repast Suite is a family of advanced, free, and open source agent-based modeling and simulation platforms that have collectively been under continuous development for over 15 years."
    11,t,SeSAm,http://www.simsesam.de/,"SeSAm (Shell for Simulated Agent Systems) provides a generic environment for modeling and experimenting with agent-based simulation. We specially focused on providing a tool for the easy construction of complex models, which include dynamic interdependencies or emergent behaviour."
    12,t,StarLogo,http://education.mit.edu/portfolio_page/starlogo-tng/,"StarLogo TNG is a downloadable programming environment that lets students and teachers create 3D games and simulations for understanding complex systems."
    13,t,Swarm,http://www.swarm.org/,"Swarm is a platform for agent-based models (ABMs) that includes a conceptual framework for designing, describing, and conducting experiments on ABMs"
    14,t,AnyLogic,http://www.anylogic.com/,"A Java Eclipse-based modeling platform that supports System Dynamics, Process-centric (AKA Discrete Event), and Agent Based Modeling."
    15,t,MATLAB,http://www.mathworks.com/products/matlab/,"MATLAB is a multi-paradigm numerical computing environment and programming language developed by MathWorks."
    16,t,AgentBase,http://agentbase.org/,"AgentBase.org allows you to do Agent Based Modeling (ABM) in the browser. You can edit, save, and share models without installing any software or even reloading the page. Models are written in Coffeescript and use the AgentBase library."
    17,f,"Agent Modeling Platform (AMP)",http://www.eclipse.org/amp/,"The AMP project provides extensible frameworks and exemplary tools for representing, editing, generating, executing and visualizing agent-based models (ABMs) and any other domain requiring spatial, behavioral and functional features."
    18,t,AgentScript,http://agentscript.org/,"AgentScript is a minimalist Agent Based Modeling (ABM) framework based on NetLogo agent semantics. Its goal is to promote the Agent Oriented Programming model in a highly deployable CoffeeScript/JavaScript implementation. "
    19,t,CRAFTY,https://www.wiki.ed.ac.uk/display/CRAFTY/Home,"CRAFTY is a large-scale ABM of land use change. It has been designed to allow efficient but powerful simulation of a wide range of land uses and the goods and services they produce. It is fully open-source and can be used without the need for any programming."
    20,t,ENVISION,http://envision.bioe.orst.edu/,"ENVISION is a GIS-based tool for scenario-based community and regional integrated planning and environmental assessments.  It provides a robust platform for integrating a variety of spatially explicit models of landscape change processes and production for conducting alternative futures analyses."
    21,t,FLAME,http://flame.ac.uk/,"FLAME is a generic agent-based modelling system which can be used to development applications in many areas. It generates a complete agent-based application which can be compiled and built on the majority of computing systems ranging from laptops to HPC super computers."
    22,t,GAMA,https://github.com/gama-platform,"GAMA is a modeling and simulation development environment for building spatially explicit agent-based simulations."
    23,t,"Insight Maker",https://insightmaker.com/,"Use Insight Maker to start with a conceptual map of your Insight and then convert it into a complete simulation model. Insight Maker supports extensive diagramming and modeling features that enable you to easily create representations of your system."
    24,t,JAMSIM,https://github.com/compassresearchcentre/jamsim,"JAMSIM is a framework for creating microsimulation models in Java. It provides code and packages for common features of microsimulation models for end users."
    25,t,JAS-mine,http://www.jas-mine.net/,"JAS-mine is a Java platform that aims at providing a unique simulation tool for discrete-event simulations, including agent-based and microsimulation models."
    26,t,Jason,https://github.com/jason-lang/jason,"Jason is an interpreter for an extended version of AgentSpeak. It implements the operational semantics of that language, and provides a platform for the development of multi-agent systems, with many user-customisable features. Jason is available as Open Source, and is distributed under GNU LGPL."
    27,t,MADeM,http://www.uv.es/grimo/jmadem/,"The MADeM (Multi-modal Agent Decision Making) model provides agents with a general mechanism to make socially acceptable decisions. In this kind of decisions, the members of an organization are required to express their preferences with regard to the different solutions for a specific decision problem. The whole model is based on the MARA (Multi-Agent Resource Allocation) theory, therefore, it represents each one of these solutions as a set of resource allocations."
    28,t,MATSim,http://www.matsim.org/,\"MATSim is an open-source framework to implement large-scale agent-based transport simulations.\""""


def flatten(ls):
    return [item for sublist in ls for item in sublist]


def load_data(model, s: str):
    f = io.StringIO(s.strip())
    rows = csv.DictReader(f)

    instances = []
    for row in rows:
        instances.append(model(**row))

    model.objects.bulk_create(instances)
    # TODO: set sequence number to start after last value when moved over to Postgres


@contextlib.contextmanager
def suppress_auto_now(model_classes, *field_names):
    _original_values = {}
    for field_name in field_names:
        _ms = model_classes if isinstance(model_classes, Iterable) else [model_classes]
        for model in _ms:
            field = model._meta.get_field(field_name)
            _original_values[field] = {
                'auto_now': field.auto_now,
                'auto_now_add': field.auto_now_add,
            }
            field.auto_now = False
            field.auto_now_add = False
    try:
        yield
    finally:
        for field, values in _original_values.items():
            field.auto_now = values['auto_now']
            field.auto_now_add = values['auto_now_add']


class Extractor:
    def __init__(self, data):
        self.data = data

    @staticmethod
    def sanitize(data: str, max_length: int = None, strip_whitespace=False) -> str:
        if strip_whitespace:
            _sanitized_data = data.replace(' ', '').lower()
        else:
            _sanitized_data = data.strip().lower()
        if max_length is not None:
            if len(_sanitized_data) > max_length:
                logger.warning("data exceeded max length %s: %s", max_length, data)
                return shorten(_sanitized_data, max_length)
        return _sanitized_data

    @staticmethod
    def sanitize_text(data: str, max_length: int = None) -> str:
        _sanitized_data = BeautifulSoup(data.strip(), "lxml").get_text()
        if max_length is not None:
            return shorten(_sanitized_data, max_length)
        return _sanitized_data

    @staticmethod
    def int_to_bool(integer_value, default=False) -> bool:
        try:
            return bool(int(integer_value))
        except:
            logger.debug("Could not convert %s to bool", integer_value)
            return default

    @classmethod
    def from_file(cls, filename):
        with open(filename, 'r', encoding='UTF-8') as f:
            data = json.load(f)
            return cls(data)


class EventExtractor(Extractor):
    EVENT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

    @staticmethod
    def parse_event_date_string(date_string: str):
        return datetime.strptime(date_string, EventExtractor.EVENT_DATE_FORMAT)

    def _extract(self, raw_event, user_id_map: Dict[str, int]) -> Event:
        summary = self.sanitize_text(get_first_field(raw_event, 'body', attribute_name='summary', default=''),
                                     max_length=300)
        description = self.sanitize_text(get_first_field(raw_event, 'body'))
        return Event(
            title=raw_event['title'],
            date_created=to_datetime(raw_event['created']),
            last_modified=to_datetime(raw_event['changed']),
            summary=summary,
            description=description,
            early_registration_deadline=to_datetime(get_first_field(raw_event, 'field_earlyregistration')),
            submission_deadline=to_datetime(get_first_field(raw_event, 'field_submissiondeadline')),
            start_date=self.parse_event_date_string(get_first_field(raw_event, 'field_eventdate')),
            end_date=self.parse_event_date_string(get_first_field(raw_event, 'field_eventdate', 'value2')),
            submitter_id=user_id_map.get(raw_event['uid'], 3)
        )

    def extract_all(self, user_id_map: Dict[str, int]):
        events = [self._extract(raw_event, user_id_map) for raw_event in self.data]
        with suppress_auto_now(Event, 'last_modified', 'date_created'):
            Event.objects.bulk_create(events)


class JobExtractor(Extractor):
    def _extract(self, raw_job: Dict, user_id_map: Dict[str, int]):
        description = get_first_field(raw_job, 'body')
        summary = summarize_to_text(description, sentences_count=2)
        return Job(
            title=raw_job['title'],
            date_created=to_datetime(raw_job['created']),
            last_modified=to_datetime(raw_job['changed']),
            summary=summary,
            description=self.sanitize_text(description),
            submitter_id=user_id_map.get(raw_job['uid'], 3)
        )

    def extract_all(self, user_id_map: Dict[str, int]):
        jobs = []
        for forum_post in self.data:
            if forum_post['forum_tid'] == "13":
                jobs.append(self._extract(forum_post, user_id_map))
        with suppress_auto_now(Job, 'last_modified', 'date_created'):
            Job.objects.bulk_create(jobs)


class UserExtractor(Extractor):
    (ADMIN_GROUP, EDITOR_GROUP, MEMBER_GROUP, REVIEWER_GROUP) = ComsesGroups.initialize()

    @staticmethod
    def _extract(raw_user):
        """ assumes existence of editor, reviewer, full_member, admin groups """
        username = Extractor.sanitize(raw_user['name'], strip_whitespace=True)
        email = Extractor.sanitize(raw_user['mail'])
        if not all([username, email]):
            logger.warning("No username or email set: %s", [username, email])
            return
        user, created = User.objects.get_or_create(
            username=username,
            email=email,
            defaults={
                "date_joined": to_datetime(raw_user['created']),
                "last_login": to_datetime(raw_user['login']),
            }
        )

        user.drupal_uid = raw_user['uid']
        roles = raw_user['roles'].values()
        """
        FIXME: home.apps isn't loading despite documentation stating that it should with a management command
        (https://docs.djangoproject.com/en/1.10/ref/applications/#initialization-process)
        so MemberProfile syncing with Users isn't happening and must be manually driven.
        """
        MemberProfile.objects.get_or_create(user=user, defaults={"timezone": raw_user['timezone']})
        if 'administrator' in roles:
            user.is_staff = True
            user.is_superuser = True
            user.save()
            user.groups.add(UserExtractor.ADMIN_GROUP)
            user.groups.add(UserExtractor.MEMBER_GROUP)
        if 'comses member' in roles:
            user.groups.add(UserExtractor.MEMBER_GROUP)
            user.groups.add(UserExtractor.REVIEWER_GROUP)
        if 'comses editor' in roles:
            user.groups.add(UserExtractor.EDITOR_GROUP)
        if 'comses reviewer' in roles:
            user.groups.add(UserExtractor.REVIEWER_GROUP)
        return user

    def extract_all(self):
        """
        Returns a mapping of drupal user ids to Django User pks.
        :return: dict
        """
        user_id_map = {}
        for raw_user in self.data:
            user = UserExtractor._extract(raw_user)
            if user:
                user_id_map[user.drupal_uid] = user.pk
        return user_id_map


class ProfileExtractor(Extractor):
    def extract_all(self, user_id_map, tag_id_map):
        contributors = []
        for raw_profile in self.data:
            drupal_uid = raw_profile['uid']
            user_id = user_id_map.get(drupal_uid, -1)
            if user_id == -1:
                logger.warning("Drupal UID %s not found in user id map, skipping", drupal_uid)
                continue
            user = User.objects.get(pk=user_id)
            user.first_name = get_first_field(raw_profile, 'field_profile2_firstname')
            user.last_name = get_first_field(raw_profile, 'field_profile2_lastname')
            member_profile = user.member_profile
            member_profile.research_interests = get_first_field(raw_profile, 'field_profile2_research')
            raw_institutions = get_field(raw_profile, 'field_profile2_institutions')
            if raw_institutions:
                raw_institution = raw_institutions[0]
                institution, created = Institution.objects.get_or_create(name=raw_institution['title'], url=raw_institution['url'])
                member_profile.institution = institution
            member_profile.degrees = get_field_attributes(raw_profile, 'field_profile2_degrees') or []
            member_profile.personal_url = get_first_field(raw_profile, 'field_profile2_personal_link', attribute_name='url')

            # crude aggregation of the wretched smorgasbord of incoming urls
            linkedin_url = get_first_field(raw_profile, 'field_profile2_linkedin_link',
                                           attribute_name='url')
            academia_edu_url = get_first_field(raw_profile, 'field_profile2_academiaedu_link',
                                               attribute_name='url')
            cv_url = get_first_field(raw_profile, 'field_profile2_cv_link', attribute_name='url')
            institutional_homepage_url = get_first_field(raw_profile, 'field_profile2_institution_link',
                                                         attribute_name='url')
            researchgate_url = get_first_field(raw_profile, 'field_profile2_researchgate_link',
                                               attribute_name='url')
            member_profile.professional_url = institutional_homepage_url \
                or researchgate_url \
                or academia_edu_url \
                or cv_url \
                or linkedin_url
            for url in ('professional_url', 'personal_url'):
                if len(getattr(member_profile, url, '')) > 200:
                    logger.warning("Ignoring overlong %s URL %s", url, getattr(member_profile, url))
                    setattr(member_profile, url, '')
            tags = flatten([tag_id_map[tid] for tid in
                            get_field_attributes(raw_profile, 'taxonomy_vocabulary_6', attribute_name='tid') if
                            tid in tag_id_map])
            member_profile.keywords.add(*tags)
            member_profile.save()
            user.save()
            try:
                contributor = Contributor.objects.get(given_name=user.first_name, family_name=user.last_name)
                contributor.email = user.email
                contributor.user = user
                contributor.save()
            except:
                contributors.append(
                    Contributor(given_name=user.first_name,
                                family_name=user.last_name,
                                email=user.email,
                                user=user))
        Contributor.objects.bulk_create(contributors)


class TaxonomyExtractor(Extractor):
    # DELIMITERS = (';', ',', '.')
    DELIMITER_REGEX = re.compile(r';|,|\.')

    def extract_all(self):
        tag_id_map = defaultdict(list)
        for raw_tag in self.data:
            if raw_tag['vocabulary_machine_name'] == 'vocabulary_6':
                raw_tag_name = raw_tag['name']
                tags = [raw_tag_name]
                # if the taxonomy was manually delimited by semicolons, commas, or periods and not split by Drupal
                # try, in that order, to split them
                tags = filter(lambda x: x.strip(), re.split(self.DELIMITER_REGEX, raw_tag_name))
                for t in tags:
                    sanitized_tag = self.sanitize(t, max_length=100)
                    tag, created = Tag.objects.get_or_create(name=sanitized_tag)
                    tag_id_map[raw_tag['tid']].append(sanitized_tag)
        return tag_id_map


class AuthorExtractor(Extractor):
    def _extract(self, raw_author):
        given_name = get_first_field(raw_author, 'field_model_authorfirst', default='')
        middle_name = get_first_field(raw_author, 'field_model_authormiddle', default='')
        family_name = get_first_field(raw_author, 'field_model_authorlast', default='')
        if any([given_name, middle_name, family_name]):
            contributor, created = Contributor.objects.get_or_create(
                given_name=given_name,
                family_name=family_name,
                defaults={'middle_name': middle_name}
            )
            contributor.item_id = raw_author['item_id']
            return contributor
        return None

    def extract_all(self):
        author_id_map = {}
        contributors = []
        for raw_author in self.data:
            c = self._extract(raw_author)
            if c:
                author_id_map[c.item_id] = c.pk
                contributors.append(c)
        return author_id_map


class ModelExtractor(Extractor):
    def _extract(self, raw_model, user_id_map, author_id_map):
        raw_author_ids = [raw_author['value'] for raw_author in get_field(raw_model, 'field_model_author')]
        author_ids = [author_id_map[raw_author_id] for raw_author_id in raw_author_ids]
        submitter_id = user_id_map[raw_model.get('uid')]
        with suppress_auto_now(Codebase, 'last_modified'):
            last_changed = to_datetime(raw_model['changed'])
            handle = get_first_field(raw_model, 'field_model_handle', default=None)
            peer_reviewed = self.int_to_bool(get_first_field(raw_model, 'field_model_certified', default=0))
            # set peer reviewed codebases as featured
            featured = self.int_to_bool(get_first_field(raw_model, 'field_model_featured', default=0)) or peer_reviewed
            code = Codebase.objects.create(
                title=raw_model['title'].strip(),
                description=self.sanitize_text(get_first_field(raw_model, field_name='body', default='')),
                summary=self.sanitize_text(
                    get_first_field(raw_model, field_name='body', attribute_name='summary', default=''),
                    max_length=500
                ),
                date_created=to_datetime(raw_model['created']),
                live=self.int_to_bool(raw_model['status']),
                first_published_at=to_datetime(raw_model['created']),
                last_published_on=last_changed,
                last_modified=last_changed,
                doi=handle,
                uuid=raw_model['uuid'],
                is_replication=Extractor.int_to_bool(get_first_field(raw_model, 'field_model_replicated', default='0')),
                references_text=get_first_field(raw_model, 'field_model_reference', default=''),
                associated_publication_text=get_first_field(raw_model, 'field_model_publication_text', default=''),
                identifier=raw_model['nid'],
                submitter_id=submitter_id,
                featured=featured,
                peer_reviewed=peer_reviewed
            )

            code.author_ids = author_ids
            code.keyword_tids = get_field_attributes(raw_model, 'taxonomy_vocabulary_6', attribute_name='tid')
        return code

    def extract_all(self, user_id_map, tag_id_map, author_id_map):
        model_code_list = [self._extract(raw_model, user_id_map, author_id_map) for raw_model in self.data]
        model_id_map = {}

        for model_code in model_code_list:
            model_code.cached_contributors = []
            for idx, author_id in enumerate(model_code.author_ids):
                model_code.cached_contributors.append(
                    CodebaseContributor(contributor_id=author_id, index=idx)
                )
            # NOTE: some tids may have been converted to multiple tags due to splitting
            model_code.tags.add(*flatten([tag_id_map[tid] for tid in model_code.keyword_tids]))
            model_id_map[model_code.identifier] = model_code
        return model_id_map


class ModelVersionExtractor(Extractor):
    PROGRAMMING_LANGUAGES = [
        'other',
        'c',
        'c++',
        'java',
        'logo (variant)',
        'perl',
        'python',
    ]

    OS_LIST = [os[0] for os in OPERATING_SYSTEMS]

    def _extract(self, raw_model_version, model_id_map: Dict[str, int]):
        model_nid = get_first_field(raw_model_version, 'field_modelversion_model', attribute_name='nid')
        platform_id = int(get_first_field(raw_model_version, 'field_modelversion_platform', default=0))
        license_id = int(get_first_field(raw_model_version, 'field_modelversion_license', default=0))
        version_number = int(get_first_field(raw_model_version, 'field_modelversion_number', default=1))
        platform = Platform.objects.get(pk=platform_id)
        codebase = model_id_map.get(model_nid)
        if codebase:
            description = get_first_field(raw_model_version, 'body')
            language = ModelVersionExtractor.PROGRAMMING_LANGUAGES[int(
                get_first_field(raw_model_version, 'field_modelversion_language', default=0))
            ]
            language_version = get_first_field(raw_model_version, 'field_modelversion_language_ver', default='')

            dependencies = {
                'programming_language': {
                    'name': language,
                    'version': language_version,
                }
            }
            # FIXME: extract runconditions
            with suppress_auto_now([Codebase, CodebaseRelease], 'last_modified'):
                last_changed = to_datetime(raw_model_version['changed'])
                codebase_release = codebase.make_release(
                    description=self.sanitize_text(description),
                    date_created=to_datetime(raw_model_version['created']),
                    first_published_at=to_datetime(raw_model_version['created']),
                    last_modified=last_changed,
                    last_published_on=last_changed,
                    os=self.OS_LIST[int(get_first_field(raw_model_version, 'field_modelversion_os', default=0))],
                    license_id=license_id,
                    identifier=raw_model_version['vid'],
                    dependencies=dependencies,
                    submitter_id=codebase.submitter_id,
                    version_number="1.{0}.0".format(version_number - 1),
                )
                # FIXME: if these do not exist in the DB, add them to the list of tags
                codebase_release.programming_languages.add(language)
                if language_version:
                    codebase_release.programming_languages.add(language_version)
                codebase_release.platforms.add(platform)
                if platform_id == 0:
                    # check for platform_ver and add to tags if it exists
                    platform_version = get_first_field(raw_model_version, 'field_modelversion_platform_ver')
                    if platform_version:
                        codebase_release.platform_tags.add(self.sanitize(platform_version))
                else:
                    codebase_release.platform_tags.add(platform.name)
                release_contributors = []
                # re-create new CodebaseContributors for each model version
                # do not modify codebase.contributors in place or it will overwrite previous version contributors
                for contributor in codebase.cached_contributors:
                    release_contributors.append(CodebaseContributor(
                        index=contributor.index,
                        contributor_id=contributor.contributor_id,
                        release_id=codebase_release.pk
                    ))
                CodebaseContributor.objects.bulk_create(release_contributors)
                codebase_release.save()
                return raw_model_version['nid'], codebase_release.id
        else:
            logger.warning("Unable to locate parent model nid %s for version %s", model_nid, raw_model_version['vid'])
            return None

    def extract_all(self, model_id_map: Dict[str, int]):
        model_version_id_map = {}
        for raw_model_version in self.data:
            result = self._extract(raw_model_version, model_id_map)
            if result:
                drupal_id, pk = result
                model_version_id_map[drupal_id] = pk
        return model_version_id_map


class ValidationError(KeyError):
    pass


class DownloadCountExtractor:
    """
    Download data extracted the openabm website using

    ```
    SELECT id as nid, timestamp as date_created, download_count.uid, ip_address, referrer, node.type
    FROM openabm.download_count as download_count
    INNER JOIN openabm.node as node on node.nid = download_count.id
    INTO OUTFILE '/var/backups/DownloadCountAll.csv'
    FIELDS TERMINATED BY ','
        OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\n';
    ```
    """

    def __init__(self, data):
        self.data = data

    @classmethod
    def from_file(cls, file_path: str):
        with open(file_path, 'r') as f:
            return cls(list(csv.DictReader(f)))

    @staticmethod
    def _get_instance(raw_download, instance_id_map, field_name: str, message: str):
        drupal_id = raw_download[field_name]
        instance = instance_id_map.get(drupal_id)
        if instance is None:
            raise ValidationError(message.format(drupal_id))

        return instance

    @classmethod
    def _get_user_id(cls, raw_download, user_id_map):
        user = user_id_map.get(raw_download['uid'])
        if not user:
            logger.info("Unable to locate user with Drupal UID %s. Setting user NULL", raw_download['uid'])
        return user

    @classmethod
    def _get_codebase_release(cls, raw_download, model_version_id_map):
        codebase_release_id = cls._get_instance(raw_download, model_version_id_map, 'nid',
                                                "Unable to locate associated model version nid {}")
        return CodebaseRelease.objects.get(id=codebase_release_id)

    @classmethod
    def _get_codebase(cls, raw_download, model_id_map):
        return cls._get_instance(raw_download, model_id_map, 'nid',
                                 "Unable to locate associated model nid {}")

    def _extract_model(cls, raw_download, model_id_map, user_id_map):
        user_id = cls._get_user_id(raw_download, user_id_map)
        codebase = cls._get_codebase(raw_download, model_id_map)
        codebase_release = codebase.releases.first()
        return CodebaseReleaseDownload(
            date_created=to_datetime(raw_download['date_created']),
            user_id=user_id,
            release=codebase_release,
            ip_address=raw_download['ip_address'],
            referrer=Extractor.sanitize(raw_download['referrer'], max_length=500))

    @classmethod
    def _extract_model_version(cls, raw_download, model_version_id_map, user_id_map):
        user_id = cls._get_user_id(raw_download, user_id_map)
        codebase_release = cls._get_codebase_release(raw_download, model_version_id_map)
        return CodebaseReleaseDownload(
            date_created=to_datetime(raw_download['date_created']),
            user_id=user_id,
            release=codebase_release,
            ip_address=raw_download['ip_address'],
            referrer=Extractor.sanitize(raw_download['referrer'], max_length=500))

    def extract_all(self, model_id_map: Dict[str, int], model_version_id_map: Dict[str, int],
                    user_id_map: Dict[str, int]):
        """
        Some download counts in Drupal are at the Codebase Level but here they are at the CodebaseRelease level. In order
         to match the new database structure I make the assumption that all codebase level downloads occurred at the last
         release of the codebase
        """
        downloads = []
        for raw_download in self.data:
            try:
                if raw_download['type'] == 'model':
                    # FIXME: should extract to first version of Codebase.
                    download = self._extract_model(raw_download, model_id_map, user_id_map)
                elif raw_download['type'] == 'modelversion':
                    download = self._extract_model_version(raw_download, model_version_id_map, user_id_map)
                else:
                    raise ValidationError('Invalid node type %s', raw_download['type'])

                downloads.append(download)

            except ValidationError as e:
                logger.warning(e.args[0])

        CodebaseReleaseDownload.objects.bulk_create(downloads)


class IDMapper:
    def __init__(self, author_id_map, user_id_map, tag_id_map, model_id_map, model_version_id_map):
        self._maps = {
            Contributor: author_id_map,
            User: user_id_map,
            CodebaseTag: tag_id_map,
            Codebase: model_id_map,
            CodebaseRelease: model_version_id_map
        }

    def __getitem__(self, item):
        return self._maps[item]


def load_platforms():
    Platform.objects.all().delete()
    load_data(Platform, PLATFORMS)


def load_licenses():
    License.objects.all().delete()
    load_data(License, LICENSES)


def load(directory: str):
    # TODO: associate picture with profile
    author_extractor = AuthorExtractor.from_file(os.path.join(directory, "Author.json"))
    user_extractor = UserExtractor.from_file(os.path.join(directory, "User.json"))
    event_extractor = EventExtractor.from_file(os.path.join(directory, "Event.json"))
    job_extractor = JobExtractor.from_file(os.path.join(directory, "Forum.json"))
    model_extractor = ModelExtractor.from_file(os.path.join(directory, "Model.json"))
    model_version_extractor = ModelVersionExtractor.from_file(os.path.join(directory, "ModelVersion.json"))
    taxonomy_extractor = TaxonomyExtractor.from_file(os.path.join(directory, "Taxonomy.json"))
    profile_extractor = ProfileExtractor.from_file(os.path.join(directory, "Profile2.json"))
    download_extractor = DownloadCountExtractor.from_file(os.path.join(directory, "DownloadCount.csv"))

    load_licenses()

    load_platforms()

    # extract Codebase Authors, then try to correlate with existing Users
    author_id_map = author_extractor.extract_all()
    # extract Users first so that we have a remote chance of correlating Authors with Users
    user_id_map = user_extractor.extract_all()
    # extract Drupal taxonomy terms
    tag_id_map = taxonomy_extractor.extract_all()
    # profile extraction adds first name / last name and MemberProfile fields to Users.
    profile_extractor.extract_all(user_id_map, tag_id_map)

    job_extractor.extract_all(user_id_map)
    event_extractor.extract_all(user_id_map)

    model_id_map = model_extractor.extract_all(user_id_map, tag_id_map, author_id_map)
    model_version_id_map = model_version_extractor.extract_all(model_id_map)

    download_extractor.extract_all(model_id_map, model_version_id_map, user_id_map)
    return IDMapper(author_id_map, user_id_map, tag_id_map, model_id_map, model_version_id_map)
