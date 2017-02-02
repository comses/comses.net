import csv
import io
import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict

import pytz
from django.contrib.auth.models import User, Group
from taggit.models import Tag

from home.models import Event, Job, MemberProfile
from library.models import (Contributor, Codebase, CodebaseRelease, CodebaseKeyword, License,
                            CodebaseContributor, Platform, OPERATING_SYSTEMS)
from .utils import get_first_field, get_field, get_field_attributes

logger = logging.getLogger(__name__)


LICENSES = """id,name,url
    0,"None",""
    1,"GNU GPLv2",http://www.gnu.org/licenses/gpl-2.0.html
    2,"GNU GPLv3",http://www.gnu.org/licenses/gpl-3.0.html
    3,"Apache License, Version 2.0",http://www.apache.org/licenses/LICENSE-2.0.html
    4,"Creative Commons (cc by)",http://creativecommons.org/licenses/by/3.0/
    5,"Creative Commons (cc by-sa)",http://creativecommons.org/licenses/by-sa/3.0/
    6,"Creative Commons (cc by-nd)",http://creativecommons.org/licenses/by-nd/3.0
    7,"Creative Commons (cc by-nc)",http://creativecommons.org/licenses/by-nc/3.0
    8,"Creative Commons (cc by-nc-sa)",http://creativecommons.org/licenses/by-nc-sa/3.0
    9,"Creative Commons (cc by-nc-nd)",http://creativecommons.org/licenses/by-nc-nd/3.0
    10,"Academic Free License 3.0",http://www.opensource.org/licenses/afl-3.0.php
    11,"BSD 2-Clause",http://opensource.org/licenses/BSD-2-Clause
    12,"MIT License", https://opensource.org/licenses/MIT"""

PLATFORMS = """id,name,url
    0,Other,NULL
    1,"Ascape",http://ascape.sourceforge.net/
    2,Breve,http://www.spiderland.org/
    3,Cormas,http://cormas.cirad.fr/en/outil/outil.htm
    4,DEVS,http://acims.asu.edu/software/devs-suite/
    5,Ecolab,http://ecolab.sourceforge.net/
    6,Mason,http://cs.gmu.edu/~eclab/projects/mason/
    7,MASS,http://mass.aitia.ai/
    8,MobilDyc,http://w3.avignon.inra.fr/mobidyc/index.php/English_summary
    9,NetLogo,http://ccl.northwestern.edu/netlogo/
    10,Repast,http://repast.github.io
    11,Sesam,http://www.simsesam.de/
    12,StarLogo,http://education.mit.edu/starlogo/
    13,Swarm,http://www.swarm.org/
    14,AnyLogic,http://www.anylogic.com/
    15,Matlab,http://www.mathworks.com/products/matlab/"""


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


class Extractor:
    def __init__(self, data):
        self.data = data

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

    @staticmethod
    def to_datetime(drupal_datetime_string: str, tz=pytz.UTC):
        if drupal_datetime_string.strip():
            # majority of incoming Drupal datetime strings are unix timestamps, e.g.,
            # http://drupal.stackexchange.com/questions/45443/why-timestamp-format-was-chosen-for-users-created-field
            try:
                return datetime.fromtimestamp(float(drupal_datetime_string), tz=tz)
            except:
                logger.exception("Could not convert as a timestamp: %s", drupal_datetime_string)
            # occasionally they are also date strings like '2010-08-01 00:00:00'
            try:
                return datetime.strptime(drupal_datetime_string, '%Y-%m-%d %H:%M:%S')
            except:
                logger.exception("Could not convert as a datetime string: %s", drupal_datetime_string)
            # give up at this point, fall through to return None
        return None


class EventExtractor(Extractor):
    EVENT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

    @staticmethod
    def parse_event_date_string(date_string: str):
        return datetime.strptime(date_string, EventExtractor.EVENT_DATE_FORMAT)

    def _extract(self, raw_event, user_id_map: Dict[str, int]) -> Event:
        return Event(
            title=raw_event['title'],
            date_created=self.to_datetime(raw_event['created']),
            last_modified=self.to_datetime(raw_event['changed']),
            summary=get_first_field(raw_event, 'body', attribute_name='summary', default='')[:300],
            description=get_first_field(raw_event, 'body'),
            early_registration_deadline=self.to_datetime(get_first_field(raw_event, 'field_earlyregistration')),
            submission_deadline=self.to_datetime(get_first_field(raw_event, 'field_submissiondeadline')),
            start_date=self.parse_event_date_string(get_first_field(raw_event, 'field_eventdate')),
            end_date=self.parse_event_date_string(get_first_field(raw_event, 'field_eventdate', 'value2')),
            submitter_id=user_id_map.get(raw_event['uid'], 3)
        )

    def extract_all(self, user_id_map: Dict[str, int]):
        events = [self._extract(raw_event, user_id_map) for raw_event in self.data]
        Event.objects.bulk_create(events)


class JobExtractor(Extractor):
    def _extract(self, raw_job: Dict, user_id_map: Dict[str, int]):
        return Job(
            title=raw_job['title'],
            date_created=self.to_datetime(raw_job['created']),
            last_modified=self.to_datetime(raw_job['changed']),
            description=get_first_field(raw_job, 'body'),
            submitter_id=user_id_map.get(raw_job['uid'], 3)
        )

    def extract_all(self, user_id_map: Dict[str, int]):
        jobs = []
        for forum_post in self.data:
            if forum_post['forum_tid'] == "13":
                jobs.append(self._extract(forum_post, user_id_map))
        Job.objects.bulk_create(jobs)


class UserExtractor(Extractor):

    ADMIN_GROUP, c = Group.objects.get_or_create(name='Admins')
    EDITOR_GROUP, c = Group.objects.get_or_create(name='Editors')
    REVIEWER_GROUP, c = Group.objects.get_or_create(name='Reviewers')
    MEMBER_GROUP, c = Group.objects.get_or_create(name='Full Members')

    @staticmethod
    def _extract(raw_user):
        """ assumes existence of editor, reviewer, full_member, admin groups """
        username = raw_user['name']
        email = raw_user['mail']
        if not all([username, email]):
            return
        user, created = User.objects.get_or_create(
            username=username,
            email=email,
            defaults={
                "date_joined": Extractor.to_datetime(raw_user['created']),
                "last_login": Extractor.to_datetime(raw_user['login']),
            }
        )
        user.drupal_uid = raw_user['uid']
        roles = raw_user['roles'].values()
        MemberProfile.objects.get_or_create(user=user, defaults={"timezone": raw_user['timezone']})
        if 'administrator' in roles:
            user.is_superuser = True
            user.save()
            user.groups.add(UserExtractor.ADMIN_GROUP)
            user.groups.add(UserExtractor.MEMBER_GROUP)
        if 'comses member' in roles:
            user.groups.add(UserExtractor.MEMBER_GROUP)
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
        users = [UserExtractor._extract(raw_user) for raw_user in self.data]
        user_id_map = dict([(user.drupal_uid, user.pk) for user in users if user is not None])
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
            profile = user.member_profile
            user.first_name = get_first_field(raw_profile, 'field_profile2_firstname')
            user.last_name = get_first_field(raw_profile, 'field_profile2_lastname')
            contributors.append(Contributor(
                given_name=user.first_name,
                middle_name=get_first_field(raw_profile, 'field_profile2_middlename'),
                family_name=user.last_name,
                email=user.email,
                user=user))
            profile.research_interests = get_first_field(raw_profile, 'field_profile2_research')
            profile.institutions = get_field(raw_profile, 'institutions')
            profile.degrees = get_field_attributes(raw_profile, 'field_profile2_degrees')
            profile.academia_edu_url = get_first_field(raw_profile, 'field_profile2_academiaedu_link',
                                                       attribute_name='url')
            profile.cv_url = get_first_field(raw_profile, 'field_profile2_cv_link', attribute_name='url')
            profile.institutional_homepage_url = get_first_field(raw_profile, 'field_profile2_institution_link',
                                                                 attribute_name='url')
            profile.linkedin_url = get_first_field(raw_profile, 'field_profile2_linkedin_link',
                                                   attribute_name='url')
            profile.personal_homepage_url = get_first_field(raw_profile, 'field_profile2_personal_link',
                                                            attribute_name='url')
            profile.researchgate_url = get_first_field(raw_profile, 'field_profile2_researchgate_link',
                                                       attribute_name='url')
            for url in ('academia_edu_url', 'cv_url', 'institutional_homepage_url', 'personal_homepage_url', 'researchgate_url'):
                if len(getattr(profile, url, '')) > 200:
                    logger.warning("Ignoring overlong %s URL %s", url, getattr(profile, url))
                    setattr(profile, url, '')
            tags = flatten([tag_id_map[tid] for tid in get_field_attributes(raw_profile, 'taxonomy_vocabulary_6', attribute_name='tid') if tid in tag_id_map])
            profile.keywords.add(*tags)
            profile.save()
            user.save()
        Contributor.objects.bulk_create(contributors)


class TaxonomyExtractor(Extractor):

    # DELIMITERS = (';', ',', '.')
    DELIMITER_REGEX = re.compile(r';|,|\.')

    @staticmethod
    def sanitize(tag: str) -> str:
        rv = tag.strip()
        if len(tag) > 100:
            logger.warning("tag_too_long: %s", tag)
            return tag[:100].strip()
        return rv

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
                    t = self.sanitize(t)
                    tag, created = Tag.objects.get_or_create(name=t)
                    tag_id_map[raw_tag['tid']].append(t)
        return tag_id_map


class AuthorExtractor(Extractor):
    def _extract(self, raw_author):
        contributor = Contributor(
            given_name=get_first_field(raw_author, 'field_model_authorfirst', default=''),
            middle_name=get_first_field(raw_author, 'field_model_authormiddle', default=''),
            family_name=get_first_field(raw_author, 'field_model_authorlast', default='')
        )
        contributor.item_id = raw_author['item_id']
        return contributor

    def extract_all(self):
        contributors = [self._extract(raw_author) for raw_author in self.data]
        Contributor.objects.bulk_create(contributors)
        return dict([(c.item_id, c.pk) for c in contributors])


class ModelExtractor(Extractor):

    def _extract(self, raw_model, user_id_map, author_id_map):
        raw_author_ids = [raw_author['value'] for raw_author in get_field(raw_model, 'field_model_author')]
        author_ids = [author_id_map[raw_author_id] for raw_author_id in raw_author_ids]
        code = Codebase(title=raw_model['title'].strip(),
                        description=get_first_field(raw_model, field_name='body', default=''),
                        date_created=self.to_datetime(raw_model['created']),
                        last_modified=self.to_datetime(raw_model['changed']),
                        is_replication=Extractor.int_to_bool(get_first_field(raw_model, 'field_model_replicated', default='0')),
                        references_text=get_first_field(raw_model, 'field_model_reference', default=''),
                        replication_references_text=get_first_field(raw_model, 'field_model_publication_text', default=''),
                        identifier=raw_model['nid'],
                        peer_reviewed=self.int_to_bool(get_first_field(raw_model, 'field_model_certified', default=0)),
                        submitter_id=user_id_map[raw_model.get('uid')])
        code.author_ids = author_ids
        code.keyword_tids = get_field_attributes(raw_model, 'taxonomy_vocabulary_6', attribute_name='tid')
        return code

    def extract_all(self, user_id_map, tag_id_map, author_id_map):
        model_code_list = [self._extract(raw_model, user_id_map, author_id_map) for raw_model in self.data]
        model_id_map = {}
        contributors = []
        for model_code in model_code_list:
            model_code.save()
            for idx, author_id in enumerate(model_code.author_ids):
                contributors.append(
                    CodebaseContributor(contributor_id=author_id,
                                        codebase_id=model_code.pk,
                                        index=idx)
                )
            # FIXME: some tids may have been converted to multiple tags due to splitting
            model_code.keywords.add(*flatten([tag_id_map[tid] for tid in model_code.keyword_tids]))
            model_id_map[model_code.identifier] = model_code
        CodebaseContributor.objects.bulk_create(contributors)
        return model_id_map


class ModelVersionExtractor(Extractor):

    PROGRAMMING_LANGUAGES = [
        'Other',
        'C',
        'C++',
        'Java',
        'Logo (variant)',
        'Perl',
        'Python',
    ]

    OS_LIST = [os[0] for os in OPERATING_SYSTEMS]

    def _extract(self, raw_model_version, model_id_map: Dict[str, int]):
        model_nid = get_first_field(raw_model_version, 'field_modelversion_model', attribute_name='nid')
        platform_id = int(get_first_field(raw_model_version, 'field_modelversion_platform', default=0))
        license_id = int(get_first_field(raw_model_version, 'field_modelversion_license', default=0))
        version_number = int(get_first_field(raw_model_version, 'field_modelversion_number', default=1))
        platform = Platform.objects.get(pk=platform_id)
        code = model_id_map.get(model_nid)
        if code:
            description = get_first_field(raw_model_version, 'body')
            language = self.PROGRAMMING_LANGUAGES[int(get_first_field(raw_model_version, 'field_modelversion_language',
                                                                      default=0))]
            dependencies = {
                'programming_language': {
                    'name': language,
                    'version': get_first_field(raw_model_version, 'field_modelversion_language_ver', default='')
                }
            }
            model_version = code.make_release(
                description=description,
                date_created=self.to_datetime(raw_model_version['created']),
                last_modified=self.to_datetime(raw_model_version['changed']),
                os=self.OS_LIST[int(get_first_field(raw_model_version, 'field_modelversion_os', default=0))],
                license_id=license_id,
                identifier=raw_model_version['vid'],
                dependencies=dependencies,
                submitter=code.submitter,
                version_number="1.{0}.0".format(version_number-1),
            )
            model_version.programming_languages.add(language)
            model_version.platforms.add(platform.name)
            # FIXME: add files
            return raw_model_version['nid'], model_version.id
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


class IDMapper:
    def __init__(self, author_id_map, user_id_map, tag_id_map, model_id_map, model_version_id_map):
        self._maps = {
            Contributor: author_id_map,
            User: user_id_map,
            CodebaseKeyword: tag_id_map,
            Codebase: model_id_map,
            CodebaseRelease: model_version_id_map
        }

    def __getitem__(self, item):
        return self._maps[item]


def load(directory: str):
    # TODO: associate picture with profile
    author_extractor = AuthorExtractor.from_file(os.path.join(directory, "Author.json"))
    event_extractor = EventExtractor.from_file(os.path.join(directory, "Event.json"))
    job_extractor = JobExtractor.from_file(os.path.join(directory, "Forum.json"))
    model_extractor = ModelExtractor.from_file(os.path.join(directory, "Model.json"))
    model_version_extractor = ModelVersionExtractor.from_file(os.path.join(directory, "ModelVersion.json"))
    taxonomy_extractor = TaxonomyExtractor.from_file(os.path.join(directory, "Taxonomy.json"))
    profile_extractor = ProfileExtractor.from_file(os.path.join(directory, "Profile2.json"))
    user_extractor = UserExtractor.from_file(os.path.join(directory, "User.json"))

    if License.objects.count() == 0:
        load_data(License, LICENSES)
    if Platform.objects.count() == 0:
        load_data(Platform, PLATFORMS)

    author_id_map = author_extractor.extract_all()
    user_id_map = user_extractor.extract_all()
    job_extractor.extract_all(user_id_map)
    event_extractor.extract_all(user_id_map)
    tag_id_map = taxonomy_extractor.extract_all()
    model_id_map = model_extractor.extract_all(user_id_map, tag_id_map, author_id_map)
    model_version_id_map = model_version_extractor.extract_all(model_id_map)
    profile_extractor.extract_all(user_id_map, tag_id_map)
    return IDMapper(author_id_map, user_id_map, tag_id_map, model_id_map, model_version_id_map)
