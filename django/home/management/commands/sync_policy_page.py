"""Synchronize About policies, publishing first versions for feedback."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from home.content_sync import save_source_revision, update_fields
from home.models import CategoryIndexPage, MarkdownPage
from wagtail.models import Page

POLICY_DOCUMENTS = (
    ("policy", "CoMSES Policies"),
    ("data-privacy", "Data Protection and Privacy"),
)

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content"


class Command(BaseCommand):
    help = "Sync About policies; publish first versions and save later changes as drafts."

    def add_arguments(self, parser):
        parser.add_argument("--draft", action="store_true", help="Keep initial pages unpublished for preview.")

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
            self.sync_page(parent, *content, publish_initial=not options["draft"])
        self.stdout.write(self.style.SUCCESS("Policies synchronized. Review later changes in Wagtail."))

    def sync_page(self, parent, slug, title, content, *, publish_initial):
        existing = Page.objects.child_of(parent).filter(slug=slug).first()
        if existing:
            if not isinstance(existing.specific, MarkdownPage):
                raise CommandError(f"An existing {slug} page has a different type; review it in Wagtail.")
            page = existing.specific.get_latest_revision_as_object()
            changed = update_fields(page, {"body": content})
            revision, published = save_source_revision(page, changed=changed, publish_initial=publish_initial)
            if published:
                self.stdout.write(f"Published initial page: {existing.url}")
            elif revision:
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
        _, published = save_source_revision(page, changed=True, publish_initial=publish_initial)
        action = "Published initial page" if published else "Created draft"
        self.stdout.write(f"{action}: {page.url}")
        return page
