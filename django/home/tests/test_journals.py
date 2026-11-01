from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from wagtail.models import Page

from home.models import Journal, JournalIndexPage, JournalSnippetPlacement


class JournalIndexPageTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = Page.get_first_root_node().add_child(
            instance=JournalIndexPage(title="Journals", slug="test-journals")
        )
        cls.journals = []
        for index in range(5):
            journal = Journal.objects.create(
                name=f"Journal {index}",
                url=f"https://example.org/journal-{index}/",
                description=f"Description {index}",
            )
            journal.tags.add(f"topic-{index}")
            cls.journals.append(journal)

    def test_render_queries_do_not_grow_with_placements(self):
        request = RequestFactory().get("/resources/journals/")
        request.user = AnonymousUser()
        request.csp_nonce = "test-nonce"
        for count in (1, 5):
            with self.subTest(placements=count):
                JournalSnippetPlacement.objects.filter(page=self.page).delete()
                for journal in self.journals[:count]:
                    JournalSnippetPlacement.objects.create(page=self.page, journal=journal)
                page = JournalIndexPage.objects.get(pk=self.page.pk)
                with self.assertNumQueries(3):
                    context = page.get_context(request)
                self.assertEqual(
                    [placement.journal.pk for placement in context["journal_placements"]],
                    [journal.pk for journal in self.journals[:count]],
                )
                with CaptureQueriesContext(connection) as queries:
                    response = page.serve(request)
                    response.render()
                journal_queries = [
                    query["sql"]
                    for query in queries
                    if any(table in query["sql"] for table in ("home_journal", "taggit_tag"))
                ]
                self.assertEqual(len(journal_queries), 3)
                for index in range(count):
                    self.assertContains(response, f"Journal {index}")
                    self.assertContains(response, f"Description {index}")
                    self.assertContains(response, f"topic-{index}")
                    self.assertContains(response, self.journals[index].url)

    def test_preview_uses_unsaved_placements(self):
        page = JournalIndexPage.objects.get(pk=self.page.pk)
        JournalSnippetPlacement.objects.create(page=page, journal=self.journals[0])
        page.journal_placements.set([JournalSnippetPlacement(journal_id=self.journals[1].pk)])
        with self.assertNumQueries(2):
            context = page.get_context(RequestFactory().get("/resources/journals/"))
        with self.assertNumQueries(0):
            placements = context["journal_placements"]
            self.assertEqual([placement.journal.name for placement in placements], ["Journal 1"])
            self.assertEqual([tag.name for tag in placements[0].journal.tags.all()], ["topic-1"])

    def test_empty_page(self):
        page = JournalIndexPage.objects.get(pk=self.page.pk)
        with self.assertNumQueries(1):
            context = page.get_context(RequestFactory().get("/resources/journals/"))
        self.assertEqual(context["journal_placements"], [])
