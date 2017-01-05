import csv
import io
import json
import os
import pytz

from datetime import datetime
from django.contrib.auth.models import User, Group
from django.utils import translation
from library.models import Contributor, Code, CodeRelease, CodeKeyword, License, Platform
from home.models import Event, Job, MemberProfile
from taggit.models import Tag
from typing import Dict, List

from .utils import get_first_field, get_field, get_field_attributes

def load_data(model, s: str) -> Dict[int, Dict]:
    f = io.StringIO(s.strip())
    rows = csv.DictReader(f)

    instances = []
    for row in rows:
        instances.append(model(**row))

    model.objects.bulk_create(instances)
    # TODO: set sequence number to start after last value when moved over to Postgres


LICENSES = """id,name,url
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


class Extractor:
    def __init__(self, data):
        self.data = data

    @classmethod
    def from_file(cls, file_name):
        with open(file_name, 'r', encoding='UTF-8') as f:
            data = json.load(f)
            return cls(data)

    @staticmethod
    def to_datetime(unix_timestamp: str, tz: datetime.tzinfo=pytz.UTC):
        return datetime.fromtimestamp(float(unix_timestamp), tz=tz)


class EventExtractor(Extractor):
    def _extract(self, raw_event, user_id_map: Dict[str, int]) -> Event:
        return Event(
            title=raw_event['title'],
            date_created=self.to_datetime(raw_event['created']),
            last_modified=self.to_datetime(raw_event['changed']),
            description=get_first_field(raw_event, 'body', 'value'),
            early_registration_deadline=get_first_field(raw_event, 'field_earlyregistration', 'value', None),
            submission_deadline=get_first_field(raw_event, 'field_submissiondeadline', 'value', None),
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
            description=raw_job['body']['und'][0]['value'],
            submitter_id=user_id_map.get(raw_job['uid'], 3)
        )

    def extract_all(self, user_id_map: Dict[str, int]):
        raw_jobs = [raw_job for raw_job in self.data if raw_job['forum_tid'] == "13"]
        jobs = [self._extract(raw_job, user_id_map) for raw_job in raw_jobs]
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
        user.drupal_uid=raw_user['uid']
        roles = raw_user['roles'].values()
        MemberProfile.objects.get_or_create(user=user, defaults={"timezone":raw_user['timezone']})
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

    def extract_all(self, user_id_map, taxonomy_id_map):
        for raw_profile in self.data:
            drupal_uid = raw_profile['uid']
            user_id = user_id_map.get(drupal_uid, -1)
            if user_id == -1:
                continue
            user = User.objects.get(pk=user_id)
            profile = user.member_profile
            user.first_name = get_first_field(raw_profile, 'field_profile2_firstname')
            user.last_name = get_first_field(raw_profile, 'field_profile2_lastname')
            contributor = Contributor.objects.create(
                given_name=user.first_name,
                middle_name=get_first_field(raw_profile, 'field_profile2_middlename'),
                family_name=user.last_name,
                email=user.email,
                user=user,
            )
            profile.research_interests = get_first_field(raw_profile, 'field_profile2_research')
            profile.institutions = get_field(raw_profile, 'institutions')
            profile.degrees = get_field_attributes(raw_profile, 'field_profile2_degrees')
            profile.academia_edu_url = get_first_field(raw_profile, 'field_profile2_academiaedu_link',
                                                       attribute_name='url')
            profile.blog_url=get_first_field(raw_profile, 'field_profile2_blog_link', attribute_name='url')
            profile.cv_url=get_first_field(raw_profile, 'field_profile2_cv_link', attribute_name='url')
            profile.institutional_homepage_url=get_first_field(raw_profile, 'field_profile2_institution_link',
                                                               attribute_name='url')
            profile.linkedin_url=get_first_field(raw_profile, 'field_profile2_linkedin_link',
                                                 attribute_name='url')
            profile.personal_homepage_url=get_first_field(raw_profile, 'field_profile2_personal_link',
                                                          attribute_name='url')
            profile.research_gate_url=get_first_field(raw_profile, 'field_profile2_researchgate_link',
                                                      attribute_name='url')
            profile.keywords.add(*[taxonomy_id_map[tid] for tid in get_field_attributes(raw_profile,
                                                                                        'taxonomy_vocabulary_6',
                                                                                        attribute_name='tid')])
            profile.save()
            user.save()


class TaxonomyExtractor(Extractor):
    def extract_all(self):
        tag_id_map = {}
        for raw_tag in self.data:
            if raw_tag['vocabulary_machine_name'] == 'vocabulary_6':
                keyword, created = Tag.objects.get_or_create(name=raw_tag['name'])
                tag_id_map[raw_tag['tid']] = keyword.id
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
        return dict(
            [(c.item_id, c.pk) for c in contributors]
        )


class ModelExtractor(Extractor):
    @staticmethod
    def convert_bool_str(str):
        if str in ['0', '1']:
            return str == '1'
        else:
            raise ValueError('replication value "{}" is not valid'.format(str))

    def _extract(self, raw_model, user_id_map, author_id_map):
        content = raw_model['body']['und'][0]['value'] or ''

        raw_author_ids = [raw_author['value'] for raw_author in get_field(raw_model, 'field_model_author')]
        author_ids = [author_id_map[raw_author_id] for raw_author_id in raw_author_ids]
        return (Code(title=raw_model['title'],
                     content=content,
                     date_created=self.to_datetime(raw_model['created']),
                     last_modified=self.to_datetime(raw_model['changed']),
                     is_replication=self.convert_bool_str(
                         get_first_field(raw_model, 'field_model_replicated', 'value', '0')),
                     reference=get_first_field(raw_model, 'field_model_reference', 'value', ''),
                     replication_reference=get_first_field(raw_model, 'field_model_publication_text', 'value', ''),
                     submitter_id=user_id_map[raw_model.get('uid', 3)]), author_ids)

    def extract_all(self, user_id_map, tag_id_map, author_id_map):
        raw_models = [raw_model for raw_model in self.data if raw_model['body']['und'][0]['value']]
        detached_model_author_ids = [self._extract(raw_model, user_id_map, author_id_map) for raw_model in raw_models]
        nids = [raw_model['nid'] for raw_model in raw_models]

        for (detached_model, author_ids) in detached_model_author_ids:
            detached_model.save()
            for author_id in author_ids:
                detached_model.authors.add(Contributor.objects.get(id=author_id))

        models = [el[0] for el in detached_model_author_ids]
        model_id_map = dict(zip(nids, [m.id for m in models]))

        model_keywords = []
        for raw_model in raw_models:
            if raw_model['taxonomy_vocabulary_6']:
                for keyword in raw_model['taxonomy_vocabulary_6']['und']:
                    model_keyword = CodeKeyword(model_id=model_id_map[raw_model['nid']],
                                                keyword_id=tag_id_map[keyword['tid']])
                    model_keywords.append(model_keyword)
        CodeKeyword.objects.bulk_create(model_keywords)

        return model_id_map


class ModelVersionExtractor(Extractor):
    OS_LEVELS = [
        'Other',
        'Linux',
        'Apple OS X',
        'Microsoft Windows',
        'Platform Independent',
    ]

    LANGUAGE_LEVELS = [
        'Other',
        'C',
        'C++',
        'Java',
        'Logo (variant)',
        'Perl',
        'Python',
    ]

    def _load(self, raw_model_version, model_id_map: Dict[str, int]):
        model_nid = get_first_field(raw_model_version, 'field_modelversion_model', 'nid')
        content = get_first_field(raw_model_version, 'body', 'value')

        language = self.LANGUAGE_LEVELS[
            int(get_first_field(raw_model_version, 'field_modelversion_language', 'value', 0))]
        license_id = get_first_field(raw_model_version, 'field_modelversion_license', 'value', None)
        os = self.OS_LEVELS[int(get_first_field(raw_model_version, 'field_modelversion_os', 'value', 0))]
        platform_id = int(get_first_field(raw_model_version, 'field_modelversion_platform', 'value', 0))

        if model_nid and model_nid in model_id_map:
            model_version = CodeRelease(
                content=content,
                date_created=self.to_datetime(raw_model_version['created']),
                last_modified=self.to_datetime(raw_model_version['changed']),
                language=language,
                license_id=license_id,
                os=os,
                platform_id=platform_id,
                model_id=model_id_map[model_nid]
            )
            model_version.save()
            return raw_model_version['nid'], model_version.id

    def extract_all(self, model_id_map: Dict[str, int]):
        model_version_id_map = {}
        for raw_model_version in self.data:
            result = self._load(raw_model_version, model_id_map)
            if result:
                drupal_id, pk = result
                model_version_id_map[drupal_id] = pk
        return model_version_id_map


class IDMapper:
    def __init__(self, author_id_map, user_id_map, tag_id_map, model_id_map, model_version_id_map):
        self._maps = {
            Contributor: author_id_map,
            User: user_id_map,
            CodeKeyword: tag_id_map,
            Code: model_id_map,
            CodeRelease: model_version_id_map
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
    model_id_map = model_extractor.extract_all(user_id_map=user_id_map, tag_id_map=tag_id_map,
                                               author_id_map=author_id_map)
    model_version_id_map = model_version_extractor.extract_all(model_id_map)
    profile_extractor.extract_all(user_id_map, tag_id_map)

    return IDMapper(author_id_map, user_id_map, tag_id_map, model_id_map, model_version_id_map)
