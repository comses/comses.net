from collections import defaultdict
from typing import List

from wagtail.wagtailcore.models import Page
from wagtail.wagtailsearch.backends import get_search_backend
from django.apps import apps
from .models import Event, Job, MemberProfile
from library.models import Codebase
from home.models import FaqPage, PeoplePage, NewsIndexPage
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
        self.pk = pk
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
        self._indexes = self.get_index_names(indexed_models)

    def get_index_names(self, models):
        return [self._search.get_index_for_model(m).name for m in models]

    def search(self, text, models=None, start=0, size=10):
        if models is None:
            indexes = self._indexes
        else:
            indexes = self.get_index_names(models)
        response = self._search.es.search(indexes, body={
            "query": {
                "match": {
                    "_all": text
                }
            },
            "from": start,
            "size": size
        })
        total = response['hits']['total']
        results = response['hits']['hits']
        return self.process(results), total

    @classmethod
    def set_codebase_urls(cls, results: List[CodebaseSearchResult]):
        ids = [r.pk for r in results]
        ids.sort()
        codebases = Codebase.objects.filter(id__in=ids).only('identifier').order_by('id')
        for r, codebase in zip(results, codebases):
            r.url = codebase.get_absolute_url()

    @classmethod
    def set_member_profile_urls(cls, results: List[MemberProfileSearchResult]):
        try:
            ids = [r.pk for r in results]
        except Exception:
            print(results)
            raise
        ids.sort()
        member_profiles = MemberProfile.objects.filter(id__in=ids).only('user__username').order_by('id')
        for r, member_profile in zip(results, member_profiles):
            r.url = member_profile.get_absolute_url()

    @classmethod
    def set_page_urls(cls, results: List[OtherSearchResult]):
        ids = [r.pk for r in results]
        ids.sort()
        pages = Page.objects.filter(id__in=ids).order_by('id')
        for r, page in zip(results, pages):
            r.url = page.url

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
            data_slice = [data[i] for i in ids]
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
