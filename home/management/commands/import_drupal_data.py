"""
Management command for loading JSON dump of old CoMSES.net website into the new site
"""

from django.core.management.base import BaseCommand

import json
import os
from typing import Dict, List
from django.contrib.auth.models import User
from ...models import Author, Event, Job, Model, ModelVersion, ModelKeywords, Keyword, Profile
from datetime import datetime
from django.utils import translation


def get_field_first(obj, field_name, attribute_name, default=''):
    if obj[field_name]:
        return obj[field_name]['und'][0][attribute_name] or default
    else:
        return default


def get_field(obj, field_name):
    if obj[field_name]:
        return obj[field_name]['und']
    else:
        return []


class Extractor:
    def __init__(self, data):
        self.data = data

    @classmethod
    def from_file(cls, file_name):
        with open(file_name, "r") as f:
            data = json.load(f)
            return cls(data)

    @staticmethod
    def to_datetime(unix_timestamp: str):
        return datetime.fromtimestamp(float(unix_timestamp))


class EventExtractor(Extractor):
    def _extract(self, raw_event, user_id_map: Dict[str, int]):
        return Event(
            title=raw_event['title'],
            date_created=self.to_datetime(raw_event['created']),
            date_modified=self.to_datetime(raw_event['changed']),
            content=get_field_first(raw_event, 'body', 'value'),
            early_registration_deadline=get_field_first(raw_event, 'field_earlyregistration', 'value', None),
            submission_deadline=get_field_first(raw_event, 'field_submissiondeadline', 'value', None),
            creator_id=user_id_map[raw_event['uid']])

    def extract_all(self, user_id_map: Dict[str, int]):
        events = [self._extract(raw_event, user_id_map) for raw_event in self.data]
        Event.objects.bulk_create(events)


class JobExtractor(Extractor):
    def _extract(self, raw_job: Dict, user_id_map: Dict[str, int]):
        return Job(
            title=raw_job['title'],
            date_created=self.to_datetime(raw_job['created']),
            date_modified=self.to_datetime(raw_job['changed']),
            content=raw_job['body']['und'][0]['value'],
            creator_id=user_id_map[raw_job['uid']])

    def extract_all(self, user_id_map: Dict[str, int]):
        raw_jobs = [raw_job for raw_job in self.data if raw_job['forum_tid'] == "13"]
        jobs = [self._extract(raw_job, user_id_map) for raw_job in raw_jobs]
        Job.objects.bulk_create(jobs)


class UserExtractor(Extractor):
    def _uid(self, raw_user):
        return raw_user['uid']

    def _extract(self, raw_user):
        # print(raw_user)
        return User(
            username=raw_user['name'],
            email=raw_user['mail'])

    def extract_all(self):
        users = [self._extract(raw_user) for raw_user in self.data]
        uids = [self._uid(raw_user) for raw_user in self.data]
        User.objects.bulk_create(users)
        user_id_map = dict(zip(uids, [u[0] for u in User.objects.order_by('id').values_list('id')]))
        return user_id_map


class ProfileExtractor(Extractor):
    def _extract(self, raw_profile, user_id_map):
        return Profile(
            user_id=user_id_map[raw_profile['uid']],
            summary=get_field_first(raw_profile, 'field_profile2_research', 'value'),
            degrees='',  # TODO: change this to a text array field after moving to Postgres

            academia_edu=get_field_first(raw_profile, 'field_profile2_academiaedu_link', 'url'),
            blog=get_field_first(raw_profile, 'field_profile2_blog_link', 'url'),
            curriculum_vitae=get_field_first(raw_profile, 'field_profile2_cv_link', 'url'),
            institution=get_field_first(raw_profile, 'field_profile2_institution_link', 'url'),
            linkedin=get_field_first(raw_profile, 'field_profile2_linkedin_link', 'url'),
            personal=get_field_first(raw_profile, 'field_profile2_personal_link', 'url'),
            research_gate=get_field_first(raw_profile, 'field_profile2_researchgate_link', 'url'))

    def extract_all(self, user_id_map):
        detached_profiles = [self._extract(raw_profile, user_id_map) for raw_profile in self.data]
        Profile.objects.bulk_create(detached_profiles)


class TaxonomyExtractor(Extractor):
    def extract_all(self):
        raw_tags = [raw_tag for raw_tag in self.data if raw_tag['vocabulary_machine_name'] == 'vocabulary_6']
        tag_id_map = {}

        translation.activate('en')
        for raw_tag in raw_tags:
            keyword = Keyword.objects.create(name=raw_tag['name'])
            tag_id_map[raw_tag['tid']] = keyword.id

        return tag_id_map


class AuthorExtractor(Extractor):
    def _extract(self, raw_author):
        return Author(first_name=get_field_first(raw_author, 'field_model_authorfirst', 'value', ''),
                      middle_name=get_field_first(raw_author, 'field_model_authormiddle', 'value', ''),
                      last_name=get_field_first(raw_author, 'field_model_authorlast', 'value', ''))

    def extract_all(self):
        detached_authors = [self._extract(raw_author) for raw_author in self.data]
        item_ids = [raw_author['item_id'] for raw_author in self.data]
        Author.objects.bulk_create(detached_authors)
        author_id_map = dict(zip(item_ids, [a[0] for a in Author.objects.order_by('id').values_list('id')]))
        return author_id_map


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
        return (Model(title=raw_model['title'],
                      content=content,
                      date_created=self.to_datetime(raw_model['created']),
                      date_modified=self.to_datetime(raw_model['changed']),
                      is_replicated=self.convert_bool_str(
                          get_field_first(raw_model, 'field_model_replicated', 'value', '0')),
                      reference=get_field_first(raw_model, 'field_model_reference', 'value', ''),
                      replication_reference=get_field_first(raw_model, 'field_model_publication_text', 'value', ''),
                      creator_id=user_id_map[raw_model['uid']]), author_ids)

    def extract_all(self, user_id_map, tag_id_map, author_id_map):
        raw_models = [raw_model for raw_model in self.data if raw_model['body']['und'][0]['value']]
        detached_model_author_ids = [self._extract(raw_model, user_id_map, author_id_map) for raw_model in raw_models]
        nids = [raw_model['nid'] for raw_model in raw_models]

        for (detached_model, author_ids) in detached_model_author_ids:
            detached_model.save()
            for author_id in author_ids:
                detached_model.authors.add(Author.objects.get(id=author_id))

        models = [el[0] for el in detached_model_author_ids]
        model_id_map = dict(zip(nids, [m.id for m in models]))

        model_keywords = []
        for raw_model in raw_models:
            if raw_model['taxonomy_vocabulary_6']:
                for keyword in raw_model['taxonomy_vocabulary_6']['und']:
                    model_keyword = ModelKeywords(model_id=model_id_map[raw_model['nid']],
                                                  keyword_id=tag_id_map[keyword['tid']])
                    model_keywords.append(model_keyword)
        ModelKeywords.objects.bulk_create(model_keywords)

        return model_id_map


class ModelVersionExtractor(Extractor):
    def _load(self, raw_model_version, model_id_map: Dict[str, int]):
        model_nid = raw_model_version['field_modelversion_model']['und'][0]['nid']
        content = raw_model_version['body']['und'][0]['value'] if raw_model_version['body'] else ''
        content = content or ''
        if model_nid and model_nid in model_id_map:
            model_version = ModelVersion(
                content=content,
                date_created=self.to_datetime(raw_model_version['created']),
                date_modified=self.to_datetime(raw_model_version['changed']),
                model_id=model_id_map[model_nid])
            model_version.save()

    def extract_all(self, model_id_map: Dict[str, int]):
        for raw_model_version in self.data:
            self._load(raw_model_version, model_id_map)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--directory', '-d',
                            help='directory to load Drupal 7 data dump from')

    def handle(self, *args, **options):
        # TODO: associate picture with profile
        directory = options['directory']

        author_extractor = AuthorExtractor.from_file(os.path.join(directory, "Author.json"))
        event_extractor = EventExtractor.from_file(os.path.join(directory, "Event.json"))
        job_extractor = JobExtractor.from_file(os.path.join(directory, "Forum.json"))
        model_extractor = ModelExtractor.from_file(os.path.join(directory, "Model.json"))
        model_version_extractor = ModelVersionExtractor.from_file(os.path.join(directory, "ModelVersion.json"))
        profile_extractor = ProfileExtractor.from_file(os.path.join(directory, "Profile2.json"))
        taxonomy_extractor = TaxonomyExtractor.from_file(os.path.join(directory, "Taxonomy.json"))
        user_extractor = UserExtractor.from_file(os.path.join(directory, "User.json"))

        author_id_map = author_extractor.extract_all()
        user_id_map = user_extractor.extract_all()
        job_extractor.extract_all(user_id_map)
        event_extractor.extract_all(user_id_map)
        tag_id_map = taxonomy_extractor.extract_all()
        model_id_map = model_extractor.extract_all(user_id_map=user_id_map, tag_id_map=tag_id_map, author_id_map=author_id_map)
        model_version_extractor.extract_all(model_id_map)
        profile_extractor.extract_all(user_id_map)
