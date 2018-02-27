from django.test import TestCase
from taggit.models import Tag

from core.models import Event, Job
from core.tests.base import UserFactory
from curator.models import PendingTagCleanup
from home.tests.base import EventFactory, JobFactory
from library.models import Codebase
from library.tests.base import CodebaseFactory


class TagCleanupTestCase(TestCase):
    def setUp(self):
        self.user_factory = UserFactory()
        self.user = self.user_factory.create()
        self.codebase_factory = CodebaseFactory(self.user)
        self.codebase = self.codebase_factory.create()
        self.event_factory = EventFactory(self.user)
        self.event = self.event_factory.create()
        self.job_factory = JobFactory(self.user)
        self.job = self.job_factory.create()
        tag = Tag(name='a random tag')
        tag.save()

    def add_tags(self, tags):
        self.codebase.tags.add(*tags)
        self.codebase.save()
        self.event.tags.add(*tags)
        self.event.save()
        self.job.tags.add(*tags)
        self.job.save()

    def check_tag_name_presence(self, model, names):
        self.assertEqual(model.tags.filter(name__in=names).count(), len(names))

    def test_tag_many_to_many(self):
        old_tags = [Tag(name='abm'), Tag(name='agent based model (python)')]
        for t in old_tags:
            t.save()
        self.add_tags(old_tags)
        new_names = ['agent based model', 'python']
        for old_tag in old_tags:
            for new_name in new_names:
                PendingTagCleanup.objects.create(new_name=new_name, old_name=old_tag.name)
        PendingTagCleanup.objects.process()
        self.check_tag_name_presence(Event, new_names)
        self.check_tag_name_presence(Job, new_names)
        self.check_tag_name_presence(Codebase, new_names)

    def test_tag_delete(self):
        tag = Tag.objects.get(name='a random tag')
        self.add_tags([tag])
        new_names = []
        # Empty string new_value is a sentinel value for deletion
        PendingTagCleanup.objects.create(old_name='a random tag', new_name='')
        PendingTagCleanup.objects.process()
        self.assertEqual(Tag.objects.count(), 0)
        self.check_tag_name_presence(Event, new_names)
        self.check_tag_name_presence(Job, new_names)
        self.check_tag_name_presence(Codebase, new_names)
