from collections import defaultdict
from typing import Dict

from wagtail.wagtailcore.models import Page
from wagtail.wagtailsearch.backends import get_search_backend
from django.apps import apps
from .models import Event, Job, MemberProfile
from library.models import Codebase
import logging

logger = logging.getLogger(__name__)


def get_content_type(result):
    content_type_strs = result['_source']['content_type']
    model = apps.get_model(content_type_strs[-1])
    return model


class BaseSearchResult:
    def __init__(self, pk, description, score, title, tags, url, type):
        if description is not None and len(description) > 400:
            description = description[:397] + "..."
        self.description = description
        self.pk = int(pk)
        self.score = score
        self.tags = tags
        self.title = title
        self.type = type
        self.url = url

    @staticmethod
    def get_score(result):
        return result['_score']

    @staticmethod
    def get_pk(result):
        return result['_source']['pk']

    @staticmethod
    def get_tags(result):
        return result['_source']['tags']

    @staticmethod
    def get_title(result):
        return result['_source']['title']

    @staticmethod
    def get_description(result):
        return result['_source']['description']

    @staticmethod
    def get_full_name(result):
        return result['_source']['name']

    @staticmethod
    def get_research_interests(result):
        return result['_source']['research_interests']

    def __str__(self):
        return 'pk={} type={} score={}'.format(self.pk, self.type, self.score)


class EventSearchResult(BaseSearchResult):
    @classmethod
    def from_result(cls, result):
        pk = cls.get_pk(result)
        return cls(description=cls.get_description(result),
                   pk=pk,
                   score=cls.get_score(result),
                   title=cls.get_title(result),
                   tags=cls.get_tags(result),
                   type=get_content_type(result)._meta.verbose_name,
                   url=Event(pk=pk).get_absolute_url())


class JobSearchResult(BaseSearchResult):
    @classmethod
    def from_result(cls, result):
        pk = cls.get_pk(result)
        return cls(description=cls.get_description(result),
                   pk=pk,
                   score=cls.get_score(result),
                   title=cls.get_title(result),
                   tags=cls.get_tags(result),
                   type=get_content_type(result)._meta.verbose_name,
                   url=Job(pk=pk).get_absolute_url())


class MemberProfileSearchResult(BaseSearchResult):
    @classmethod
    def from_result(cls, result):
        pk = cls.get_pk(result)
        # fill in the url with one bulk operation later
        return cls(description=cls.get_research_interests(result),
                   pk=pk,
                   score=cls.get_score(result),
                   title=cls.get_full_name(result),
                   tags=cls.get_tags(result),
                   type=get_content_type(result)._meta.verbose_name,
                   url=None)


class CodebaseSearchResult(BaseSearchResult):
    @classmethod
    def from_result(cls, result):
        pk = cls.get_pk(result)
        # fill in the url with one bulk operation later
        return cls(description=cls.get_description(result),
                   pk=pk,
                   score=cls.get_score(result),
                   title=cls.get_title(result),
                   tags=cls.get_tags(result),
                   type=get_content_type(result)._meta.verbose_name,
                   url=None)


class OtherSearchResult(BaseSearchResult):
    @classmethod
    def from_result(cls, result):
        pk = cls.get_pk(result)
        return cls(description=result['_source'].get('description'),
                   pk=pk,
                   score=cls.get_score(result),
                   title=result['_source'].get('title', None),
                   tags=[],
                   type=get_content_type(result)._meta.verbose_name,
                   url=None)


class GeneralSearch:
    """Search across content types in Elasticsearch for matching objects"""

    def __init__(self, indexed_models=None):
        if indexed_models is None:
            indexed_models = [Codebase, Event, Job, MemberProfile, Page]
        self._search = get_search_backend()
        self._models = indexed_models

    def get_search_criteria_for_model(self, model, text):
        if hasattr(model, 'elasticsearch_query'):
            return model.elasticsearch_query(text)
        else:
            document_type = self._search.get_index_for_model(model).mapping_class(model).get_document_type()
            return {
                'bool': {
                    'must': {
                        'match': {
                            '_all': text
                        }
                    },
                    'filter': {
                        'type': {
                            'value': document_type
                        }
                    }
                }
            }

    def get_search_criteria(self, models, text, start, size):
        return {
            'query': {
                'bool': {
                    'should': [self.get_search_criteria_for_model(model, text) for model in models]
                }
            },
            'from': start,
            'size': size
        }

    def get_index_names(self, models):
        return [self._search.get_index_for_model(m).name for m in models]

    def search(self, text, models=None, start=0, size=10):
        if models is None:
            models = self._models

        body = self.get_search_criteria(models, text, start, size)
        response = self._search.es.search(self.get_index_names(models), body=body)
        total = response['hits']['total']
        results = response['hits']['hits']
        return self.process(results), total

    @classmethod
    def set_codebase_urls(cls, results: Dict[int, CodebaseSearchResult]):
        codebases = Codebase.objects.filter(id__in=results.keys()).only('identifier').in_bulk()
        for id in results.keys():
            results[id].url = codebases[id].get_absolute_url()

    @classmethod
    def set_member_profile_urls(cls, results: Dict[int, MemberProfileSearchResult]):
        member_profiles = MemberProfile.objects.filter(id__in=results.keys()).only('user__username').in_bulk()
        for id in results.keys():
            results[id].url = member_profiles[id].get_absolute_url()

    @classmethod
    def set_page_urls(cls, results: Dict[int, OtherSearchResult]):
        pages = Page.objects.filter(id__in=results.keys()).in_bulk()
        for id in results.keys():
            results[id].url = pages[id].url

    def process(self, results):
        data = []
        content_types = defaultdict(list)
        for i, result in enumerate(results):
            model = get_content_type(result)
            processor = PROCESS_DISPATCH.get(model)
            if processor is None:
                data.append(OtherSearchResult.from_result(result))
            else:
                data.append(processor(result))

            content_types[model].append(i)

        # add urls to results that require querying the database for more information
        # e.g. Codebase need identifer information to construct an url but that is not
        #  in the Elasticsearch index
        for model, ids in content_types.items():
            url_setter = URL_DISPATCH.get(model)
            data_slice = {data[i].pk: data[i] for i in ids}
            if url_setter:
                url_setter(data_slice)

        return data


PROCESS_DISPATCH = {
    Codebase: CodebaseSearchResult.from_result,
    Event: EventSearchResult.from_result,
    Job: JobSearchResult.from_result,
    MemberProfile: MemberProfileSearchResult.from_result
}

URL_DISPATCH = {
    Codebase: GeneralSearch.set_codebase_urls,
    MemberProfile: GeneralSearch.set_member_profile_urls,
    Page: GeneralSearch.set_page_urls
}
