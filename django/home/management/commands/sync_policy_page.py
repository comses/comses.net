"""Synchronize the compact About policy collection into Wagtail drafts."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from home.content_sync import update_fields
from home.models import CategoryIndexPage, MarkdownPage
from wagtail.models import Page

POLICY_DOCUMENTS = (
    ("policy", "CoMSES Policies"),
    ("data-privacy", "Data Protection and Privacy"),
)

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content"


class Command(BaseCommand):
    help = "Sync CoMSES Policies and Privacy under About as drafts without publishing."

    @transaction.atomic
    def handle(self, *args, **options):
        # Read every source before mutating the page tree.
        contents = []
        for slug, title in POLICY_DOCUMENTS:
            path = CONTENT_DIR / f"{slug}.md"
            try:
                body = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                raise CommandError(f"Cannot read policy source {path}: {error}") from error
            if not body.strip():
                raise CommandError(f"Policy source is empty: {path}")
            contents.append((slug, title, body))

        parents = CategoryIndexPage.objects.filter(slug="about")
        if parents.count() != 1:
            raise CommandError("Expected exactly one About category page; resolve the page tree before proceeding.")
        parent = parents.get()
        if parent.url != "/about/":
            raise CommandError("The About category page must resolve to /about/.")
        for content in contents:
            self.sync_page(parent, *content)
        self.stdout.write(self.style.SUCCESS("Policy drafts synchronized. Preview and publish through Wagtail."))

    def sync_page(self, parent, slug, title, content):
        existing = Page.objects.child_of(parent).filter(slug=slug).first()
        if existing:
            if not isinstance(existing.specific, MarkdownPage):
                raise CommandError(f"An existing {slug} page has a different type; review it in Wagtail.")
            page = existing.specific.get_latest_revision_as_object()
            if update_fields(page, {"body": content}):
                page.save_revision()
                self.stdout.write(f"Updated draft: {existing.url}")
            else:
                self.stdout.write(f"Unchanged: {existing.url}")
            return existing.specific

        page = MarkdownPage(
            title=title,
            slug=slug,
            heading="About",
            body=content,
            live=False,
            show_in_menus=False,
        )
        parent.add_child(instance=page)
        breadcrumbs = [("About", "/about/")]
        breadcrumbs.append((title, page.url))
        page.add_breadcrumbs(breadcrumbs)
        navigation = [(title, f"/about/{slug}/") for slug, title in POLICY_DOCUMENTS]
        page.add_navigation_links((*navigation, ("Contact", "/about/contact/")))
        page.save_revision()
        self.stdout.write(f"Created draft: {page.url}")
        return page
