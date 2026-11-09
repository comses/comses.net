import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase, override_settings
from wagtail.models import Page, Site

from django.core.management import call_command
from home.models import EducationPage, MarkdownPage, TutorialDetailPage


@override_settings(WAGTAILSEARCH_BACKENDS={"default": {"BACKEND": "wagtail.search.backends.database"}})
class EducationContentSyncTestCase(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug="home")
        Site.objects.all().delete()
        Site.objects.create(hostname="localhost", root_page=self.home, is_default_site=True)
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        (self.directory / "content").mkdir()
        (self.directory / "thumbnails").mkdir()
        self.index = [self.entry("first"), self.entry("external", external=True), self.entry("last")]
        for entry in self.index:
            if not entry["external"]:
                (self.directory / "content" / f"{entry['slug']}.md").write_text(f"# {entry['title']}\n")
        self.write_index()
        for name, value in (
            ("EDUCATION_CONTENT_DIR", self.directory),
            ("THUMBNAIL_DIR", self.directory / "thumbnails"),
        ):
            patcher = patch(f"home.management.commands.sync_education_pages.{name}", value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def entry(self, slug, external=False):
        return dict(
            slug=slug,
            title=slug.title(),
            description=f"About {slug}",
            external=external,
            link=f"https://example.org/{slug}",
            category="in-house",
            tags=["example"],
        )

    def write_index(self):
        (self.directory / "index.json").write_text(json.dumps(self.index))

    def sync(self):
        call_command("sync_education_pages")
        return EducationPage.objects.child_of(self.home).get(slug="education")

    def publish(self, page):
        for child in page.get_children():
            child.get_latest_revision().publish()
        page.get_latest_revision().publish()
        page.refresh_from_db()

    def test_external_entry_does_not_skip_later_tutorial_and_rerun_is_noop(self):
        page = self.sync()
        self.assertFalse(page.live)
        self.assertCountEqual(page.get_children().values_list("slug", flat=True), ["first", "last"])
        self.assertFalse(page.get_children().filter(live=True).exists())
        ids = list(page.get_children().values_list("pk", flat=True))
        counts = {p.pk: p.revisions.count() for p in [page, *page.get_children()]}
        page = self.sync()
        self.assertEqual(list(page.get_children().values_list("pk", flat=True)), ids)
        self.assertEqual({p.pk: p.revisions.count() for p in [page, *page.get_children()]}, counts)

    def test_changed_source_updates_only_drafts_and_preview_uses_pending_cards(self):
        page = self.sync()
        self.publish(page)
        page_id = page.pk
        child = TutorialDetailPage.objects.child_of(page).get(slug="last")
        child_id = child.pk
        live_body = child.body.raw
        live_title = page.cards.get(url="last").title
        self.index[2]["title"] = "Changed title"
        self.index[2]["tags"] = ["revised"]
        self.write_index()
        (self.directory / "content" / "last.md").write_text("## Revised content\n")
        page = self.sync()
        child.refresh_from_db()
        self.assertEqual(page.pk, page_id)
        self.assertEqual(child.pk, child_id)
        self.assertEqual(child.body.raw, live_body)
        self.assertEqual(page.cards.get(url="last").title, live_title)
        self.assertEqual(child.get_latest_revision_as_object().body.raw, "## Revised content\n")
        self.assertIn("<h2", child.get_latest_revision_as_object().body.rendered)
        self.assertNotIn("<h2", child.body.rendered)
        draft = page.get_latest_revision_as_object()
        context = draft.get_context(RequestFactory().get("/education/?tag=revised"))
        self.assertEqual([card.title for card in context["cards"]], ["Changed title"])
        self.assertEqual([card.url for card in context["cards_by_category"]["in-house"]], ["last"])
        revision_id = page.get_latest_revision().pk
        self.assertEqual(self.sync().get_latest_revision().pk, revision_id)

    def test_missing_later_file_fails_before_creating_pages(self):
        (self.directory / "content" / "last.md").unlink()
        with self.assertRaisesRegex(CommandError, "last: cannot read"):
            self.sync()
        self.assertFalse(EducationPage.objects.child_of(self.home).exists())

    def test_duplicate_and_invalid_slugs_fail_before_writes(self):
        for slug in ("first", "../outside"):
            with self.subTest(slug=slug):
                self.index[2]["slug"] = slug
                self.write_index()
                with self.assertRaises(CommandError):
                    self.sync()
                self.assertFalse(EducationPage.objects.child_of(self.home).exists())

    def test_omission_preserves_cards_children_and_revisions(self):
        page = self.sync()
        self.publish(page)
        child = page.get_children().get(slug="last")
        revision_id = child.get_latest_revision().pk
        self.index = self.index[:2]
        self.write_index()
        page = self.sync()
        self.assertTrue(page.get_children().filter(pk=child.pk).exists())
        self.assertEqual(child.get_latest_revision().pk, revision_id)
        self.assertIn("last", [card.url for card in page.get_latest_revision_as_object().cards.all()])

    def test_incompatible_parent_is_preserved(self):
        original = self.home.add_child(instance=MarkdownPage(title="Old education", slug="education"))
        with self.assertRaisesRegex(CommandError, "migrate its type separately"):
            self.sync()
        self.assertTrue(MarkdownPage.objects.filter(pk=original.pk).exists())

    def test_unmanaged_draft_fields_survive_sync(self):
        page = self.sync()
        child = TutorialDetailPage.objects.child_of(page).get(slug="last")
        draft = child.get_latest_revision_as_object()
        draft.jumbotron = False
        draft.save_revision()
        (self.directory / "content" / "last.md").write_text("Updated source\n")
        page = self.sync()
        child.refresh_from_db()
        self.assertFalse(child.get_latest_revision_as_object().jumbotron)
