from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from wagtail.models import Page, Site

from django.core.management import call_command
from home.management.commands.sync_policy_page import POLICY_DOCUMENTS
from home.models import CategoryIndexPage, MarkdownPage


@override_settings(WAGTAILSEARCH_BACKENDS={"default": {"BACKEND": "wagtail.search.backends.database"}})
class PolicyPageTestCase(TestCase):
    def setUp(self):
        self.root = Page.get_first_root_node().add_child(
            instance=Page(title="Policy test site", slug="policy-test-site")
        )
        Site.objects.all().delete()
        Site.objects.create(hostname="localhost", root_page=self.root, is_default_site=True)
        self.about = self.root.add_child(
            instance=CategoryIndexPage(title="About", slug="about", heading="About", summary="Test site information")
        )
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.content_path = Path(directory.name) / "policy.md"
        self.content_path.write_text("Initial canonical policy\n", encoding="utf-8")
        self.privacy_path = self.content_path.parent / "data-privacy.md"
        self.privacy_path.write_text("Existing privacy policy\n")
        self.documents_dir = self.content_path.parent / "policies"
        self.documents_dir.mkdir()
        for slug, _ in POLICY_DOCUMENTS:
            (self.documents_dir / f"{slug}.md").write_text(f"Initial {slug} policy\n")
        patcher = patch("home.management.commands.sync_policy_page.CONTENT_PATH", self.content_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def sync(self):
        call_command("sync_policy_page")
        return MarkdownPage.objects.child_of(self.about).get(slug="policy")

    def test_creates_unpublished_page_and_unchanged_rerun_is_noop(self):
        page = self.sync()
        self.assertEqual(page.url, "/about/policy/")
        self.assertFalse(page.live)
        self.assertFalse(page.show_in_menus)
        self.assertIsNone(page.first_published_at)
        revision_id = page.get_latest_revision().pk
        self.assertEqual(page.get_latest_revision_as_object().body.raw, self.content_path.read_text())
        self.assertEqual(self.sync().get_latest_revision().pk, revision_id)
        self.assertEqual(Page.objects.child_of(self.about).filter(slug="policy").count(), 1)

    def test_source_change_updates_draft_without_changing_live_content(self):
        page = self.sync()
        page.get_latest_revision().publish()
        page.refresh_from_db()
        live_revision_id = page.live_revision_id
        before = page.revisions.count()
        self.content_path.write_text("## Revised canonical policy\n", encoding="utf-8")
        page = self.sync()
        self.assertTrue(page.live)
        self.assertEqual(page.live_revision_id, live_revision_id)
        self.assertEqual(page.body.raw, "Initial canonical policy\n")
        self.assertEqual(page.get_latest_revision_as_object().body.raw, "## Revised canonical policy\n")
        self.assertIn("<h2", page.get_latest_revision_as_object().body.rendered)
        self.assertNotIn("<h2", page.body.rendered)
        self.assertEqual(page.revisions.count(), before + 1)
        revision_id = page.get_latest_revision().pk
        self.assertEqual(self.sync().get_latest_revision().pk, revision_id)

    def test_sync_replaces_cms_body_but_preserves_other_pending_edits(self):
        page = self.sync()
        draft = page.get_latest_revision_as_object()
        draft.title = "Editorial title"
        draft.description = "Pending editorial description"
        draft.body = "CMS-only policy text"
        editorial_revision = draft.save_revision()
        page = self.sync()
        updated = page.get_latest_revision_as_object()
        self.assertFalse(page.live)
        self.assertEqual(updated.title, "Editorial title")
        self.assertEqual(updated.description.raw, "Pending editorial description")
        self.assertEqual(updated.body.raw, self.content_path.read_text())
        self.assertTrue(page.revisions.filter(pk=editorial_revision.pk).exists())

    def test_source_change_on_unpublished_page_remains_unpublished(self):
        page = self.sync()
        before = page.revisions.count()
        self.content_path.write_text("Updated draft policy\n", encoding="utf-8")
        page = self.sync()
        self.assertFalse(page.live)
        self.assertIsNone(page.first_published_at)
        self.assertEqual(page.revisions.count(), before + 1)
        self.assertEqual(page.get_latest_revision_as_object().body.raw, self.content_path.read_text())

    def test_slug_collision_does_not_replace_existing_page(self):
        existing = self.about.add_child(instance=Page(title="Existing policy", slug="policy"))
        with self.assertRaisesRegex(CommandError, "different type"):
            call_command("sync_policy_page")
        self.assertTrue(Page.objects.filter(pk=existing.pk).exists())

    def test_missing_about_page_does_not_create_policy(self):
        self.about.delete()
        with self.assertRaisesRegex(CommandError, "exactly one"):
            call_command("sync_policy_page")
        self.assertFalse(MarkdownPage.objects.filter(slug="policy").exists())

    def test_collection_is_draft_only_and_rerun_preserves_revision_ids(self):
        hub = self.sync()
        children = list(MarkdownPage.objects.child_of(hub))
        self.assertEqual({p.slug for p in children}, {slug for slug, _ in POLICY_DOCUMENTS})
        privacy = MarkdownPage.objects.child_of(self.about).get(slug="data-privacy")
        self.assertEqual(privacy.url, "/about/data-privacy/")
        pages = [hub, privacy, *children]
        revisions = {p.pk: p.latest_revision_id for p in pages}
        self.assertTrue(all(not p.live for p in pages))
        self.sync()
        self.assertEqual(dict(Page.objects.filter(pk__in=revisions).values_list("pk", "latest_revision_id")), revisions)

    def test_child_update_preserves_live_content_and_unmanaged_children(self):
        hub = self.sync()
        child = MarkdownPage.objects.child_of(hub).first()
        child.get_latest_revision().publish()
        child.refresh_from_db()
        previous = child.body.raw
        unmanaged = hub.add_child(instance=Page(title="Other policy", slug="other"))
        hub_revision = hub.latest_revision_id
        (self.documents_dir / f"{child.slug}.md").write_text("## Changed child\n")
        self.sync()
        child.refresh_from_db()
        hub.refresh_from_db()
        self.assertEqual(child.body.raw, previous)
        self.assertEqual(child.get_latest_revision_as_object().body.raw, "## Changed child\n")
        self.assertIn("<h2", child.get_latest_revision_as_object().body.rendered)
        self.assertEqual(hub.latest_revision_id, hub_revision)
        self.assertTrue(Page.objects.filter(pk=unmanaged.pk).exists())

    def test_existing_privacy_page_keeps_identity_and_published_content(self):
        privacy = self.about.add_child(
            instance=MarkdownPage(title="Existing privacy", slug="data-privacy", body="Published privacy text")
        )
        privacy.save_revision().publish()
        self.sync()
        privacy.refresh_from_db()
        self.assertTrue(privacy.live)
        self.assertEqual(privacy.body.raw, "Published privacy text")
        self.assertEqual(privacy.get_latest_revision_as_object().body.raw, self.privacy_path.read_text())
        self.assertEqual(privacy.get_latest_revision_as_object().title, "Existing privacy")
        self.assertEqual(Page.objects.filter(slug="data-privacy").count(), 1)

    def test_missing_document_does_not_create_any_pages(self):
        next(self.documents_dir.iterdir()).unlink()
        with self.assertRaisesRegex(CommandError, "Cannot read policy source"):
            self.sync()
        self.assertFalse(Page.objects.child_of(self.about).exists())

    def test_child_type_conflict_rolls_back_all_updates(self):
        hub = self.sync()
        child = MarkdownPage.objects.child_of(hub).first()
        slug = child.slug
        child.delete()
        hub.refresh_from_db()
        conflicting = hub.add_child(instance=Page(title="Legacy page", slug=slug))
        before = hub.latest_revision_id
        self.content_path.write_text("Changed hub\n")
        with self.assertRaisesRegex(CommandError, "different type"):
            self.sync()
        hub.refresh_from_db()
        self.assertEqual(hub.latest_revision_id, before)
        self.assertTrue(Page.objects.filter(pk=conflicting.pk).exists())
