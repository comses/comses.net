"""Synchronize canonical policy content into an unpublished Wagtail revision."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from home.content_sync import update_fields
from home.models import CategoryIndexPage, MarkdownPage
from wagtail.models import Page

POLICY_DOCUMENTS = (
    ("terms-of-use", "Terms of Use"),
    ("content-submission", "Content Submission"),
    ("acceptable-use", "Acceptable Use"),
    ("review-publication", "Review and Publication"),
    ("copyright-licensing", "Copyright and Licensing"),
    ("accessibility", "Accessibility"),
    ("code-of-conduct", "Code of Conduct"),
    ("ai-automated-processing", "AI and Automated Processing and Generation"),
)

CONTENT_PATH = Path(__file__).resolve().parents[2] / "content" / "policy.md"


class Command(BaseCommand):
    help = "Sync the policy index and its documents to Wagtail drafts without publishing."

    @transaction.atomic
    def handle(self, *args, **options):
        # Read every source before mutating the page tree.
        sources = [("policy", "CoMSES Net Policies", CONTENT_PATH)]
        sources.extend(
            (slug, title, CONTENT_PATH.parent / "policies" / f"{slug}.md") for slug, title in POLICY_DOCUMENTS
        )
        sources.append(("data-privacy", "Data Protection and Privacy", CONTENT_PATH.parent / "data-privacy.md"))
        contents = []
        for slug, title, path in sources:
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
        hub = self.sync_page(parent, *contents[0])
        for content in contents[1:-1]:
            self.sync_page(hub, *content)
        self.sync_page(parent, *contents[-1])
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
            # Tree operations must use the persisted parent, not a pending draft.
            return existing.specific

        page = MarkdownPage(
            title=title,
            slug=slug,
            heading="About" if parent.slug == "about" else "Policies",
            body=content,
            live=False,
            show_in_menus=False,
        )
        parent.add_child(instance=page)
        breadcrumbs = [("About", "/about/")]
        if parent.slug == "policy":
            breadcrumbs.append(("Policies", "/about/policy/"))
        breadcrumbs.append((title, page.url))
        page.add_breadcrumbs(breadcrumbs)
        page.add_navigation_links((("Policies", "/about/policy/"), ("Contact", "/about/contact/")))
        page.save_revision()
        self.stdout.write(f"Created draft: {page.url}")
        return page
