import json
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import unquote, urljoin, urlsplit

from core.fields import render_sanitized_markdown, render_sanitized_tutorial_markdown
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from wagtail.models import Page, Site

from django.core.management import call_command
from home.management.commands.sync_policy_page import CONTENT_DIR, POLICY_DOCUMENTS
from home.models import CategoryIndexPage, MarkdownPage


class PolicyHTMLParser(HTMLParser):
    def __init__(self, source, renderer=render_sanitized_markdown):
        super().__init__()
        self.links = []
        self.anchors = set()
        self.callouts = []
        self.feed(renderer(source))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "admonition" in attrs.get("class", "").split():
            self.callouts.append(attrs["class"])
        if "id" in attrs:
            self.anchors.add(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])


class PolicyContentLinksTestCase(SimpleTestCase):
    def test_internal_links_resolve_across_canonical_policy_documents(self):
        sources = {f"/about/{slug}/": CONTENT_DIR / f"{slug}.md" for slug, _ in POLICY_DOCUMENTS}
        documents = {route: PolicyHTMLParser(path.read_text(encoding="utf-8")) for route, path in sources.items()}
        education = CONTENT_DIR / "education"
        for entry in json.loads((education / "index.json").read_text(encoding="utf-8")):
            if not entry["external"]:
                source = (education / "content" / f"{entry['slug']}.md").read_text(encoding="utf-8")
                documents[f"/education/{entry['slug']}/"] = PolicyHTMLParser(source, render_sanitized_tutorial_markdown)
        checked_routes = set(sources) | {"/education/sharing-models/", "/education/responsible-practices/"}
        # Existing site pages outside the source-managed collection.
        other_routes = {"/about/contact/", "/about/faq/", "/about/people/", "/reviews/", "/digest/", "/education/"}
        for route in checked_routes:
            document = documents[route]
            for href in document.links:
                with self.subTest(source=route, link=href):
                    target = urlsplit(href)
                    if target.scheme or target.netloc:
                        continue
                    target = urlsplit(urljoin(route, href))
                    path = unquote(target.path).rstrip("/") + "/"
                    self.assertIn(path, documents.keys() | other_routes, "Unknown internal policy link target")
                    if path in documents and target.fragment:
                        self.assertIn(unquote(target.fragment), documents[path].anchors, "Missing policy anchor")

    def test_policy_uses_existing_sanitized_callouts(self):
        policy = PolicyHTMLParser((CONTENT_DIR / "policy.md").read_text(encoding="utf-8"))
        self.assertIn("admonition info", policy.callouts)
        self.assertIn("terms-of-use", policy.anchors)
        self.assertIn("accessibility", policy.anchors)
        self.assertIn("#terms-of-use", policy.links)


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
        self.content_dir = Path(directory.name)
        for slug, _ in POLICY_DOCUMENTS:
            (self.content_dir / f"{slug}.md").write_text(f"Initial {slug} content\n", encoding="utf-8")
        self.content_path = self.content_dir / "policy.md"
        self.privacy_path = self.content_dir / "data-privacy.md"
        patcher = patch("home.management.commands.sync_policy_page.CONTENT_DIR", self.content_dir)
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
        self.assertEqual(page.body.raw, "Initial policy content\n")
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

    def test_collection_is_flat_draft_only_and_rerun_preserves_revision_ids(self):
        self.sync()
        pages = list(MarkdownPage.objects.child_of(self.about))
        self.assertEqual({p.slug for p in pages}, {slug for slug, _ in POLICY_DOCUMENTS})
        revisions = {p.pk: p.latest_revision_id for p in pages}
        self.assertTrue(all(not p.live for p in pages))
        for page in pages:
            self.assertEqual(page.url, f"/about/{page.slug}/")
            self.assertFalse(page.get_children().exists())
            links = {link["url"] for link in page.get_latest_revision_as_object().get_navigation_links()}
            self.assertEqual(links, {f"/about/{slug}/" for slug, _ in POLICY_DOCUMENTS} | {"/about/contact/"})
        self.sync()
        self.assertEqual(dict(Page.objects.filter(pk__in=revisions).values_list("pk", "latest_revision_id")), revisions)
        self.assertFalse(Page.objects.filter(slug="terms-of-use").exists())

    def test_unmanaged_about_pages_and_legacy_policy_children_are_retained(self):
        policy = self.sync()
        unmanaged = self.about.add_child(instance=Page(title="Other page", slug="other"))
        legacy = policy.add_child(instance=Page(title="Old Terms draft", slug="terms-of-use"))
        self.sync()
        self.assertTrue(Page.objects.filter(pk=unmanaged.pk).exists())
        self.assertTrue(Page.objects.child_of(policy).filter(pk=legacy.pk).exists())

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
        (self.content_dir / "data-privacy.md").unlink()
        with self.assertRaisesRegex(CommandError, "Cannot read policy source"):
            self.sync()
        self.assertFalse(Page.objects.child_of(self.about).exists())

    def test_later_type_conflict_rolls_back_all_updates(self):
        policy = self.sync()
        privacy = MarkdownPage.objects.child_of(self.about).get(slug="data-privacy")
        privacy.delete()
        conflicting = self.about.add_child(instance=Page(title="Legacy privacy", slug="data-privacy"))
        before = policy.latest_revision_id
        self.content_path.write_text("Changed policy\n")
        with self.assertRaisesRegex(CommandError, "different type"):
            self.sync()
        policy.refresh_from_db()
        self.assertEqual(policy.latest_revision_id, before)
        self.assertTrue(Page.objects.filter(pk=conflicting.pk).exists())

    def test_empty_source_does_not_create_any_pages(self):
        (self.content_dir / "data-privacy.md").write_text(" \n")
        with self.assertRaisesRegex(CommandError, "Policy source is empty"):
            self.sync()
        self.assertFalse(Page.objects.child_of(self.about).exists())
