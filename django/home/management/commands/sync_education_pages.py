"""Synchronize education source files into reviewable Wagtail draft revisions."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from core.fs import get_canonical_image
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from home.content_sync import update_fields
from home.models import EducationPage, TutorialCard, TutorialDetailPage
from wagtail.models import Page

HOME_DIR = Path(__file__).resolve().parents[2]
EDUCATION_CONTENT_DIR = HOME_DIR / "content" / "education"
THUMBNAIL_DIR = HOME_DIR / "static" / "education" / "thumbnails"
EDUCATION_PAGE_SLUG = "education"
EDUCATION_PAGE_TITLE = "Educational Resources"
EDUCATION_PAGE_HEADING = "Training Modules"
EDUCATION_PAGE_DESCRIPTION = (
    "CoMSES Net training modules provide guidance on good practices for computational modeling and "
    "sharing your work with [FAIR principles for research software "
    "(FAIR4RS)](https://doi.org/10.15497/RDA00068) and [FORCE11 Software Citation "
    "Principles](https://doi.org/10.7717/peerj-cs.86) in mind.\n\nOur [education "
    "forum](https://forum.comses.net/c/education) also hosts a [community curated list of additional "
    "educational resources](https://forum.comses.net/t/educational-resources/9159/2) and can be "
    "freely used to discuss, collaborate, and share additional educational resources.\n\nLearn more "
    "about the broader [Making Models FAIR](https://tobefair.org) initiative to help make "
    "computational models findable, accessible, interoperable, and reusable."
)


def read_index(directory, thumbnail_directory):
    """Validate and read every source before any page or image is changed."""
    try:
        index = json.loads((directory / "index.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise CommandError(f"Cannot read education index: {exc}") from exc
    if not isinstance(index, list):
        raise CommandError("Education index must be a list.")
    slugs, urls = set(), set()
    categories = {value for value, label in TutorialCard.EducationalContentCategory.choices}
    for entry in index:
        if not isinstance(entry, dict):
            raise CommandError("Every education entry must be an object.")
        slug = entry.get("slug")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise CommandError(f"Invalid tutorial slug: {slug!r}")
        if slug in slugs:
            raise CommandError(f"Duplicate tutorial slug: {slug}")
        slugs.add(slug)
        for key, limit in (("slug", 200), ("title", 128), ("description", 1000)):
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise CommandError(f"{slug}: {key} must be nonempty text of at most {limit} characters.")
        if not isinstance(entry.get("category"), str) or entry["category"] not in categories:
            raise CommandError(f"{slug}: invalid category.")
        if type(entry.get("external")) is not bool:
            raise CommandError(f"{slug}: external must be true or false.")
        tags = entry.get("tags")
        if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
            raise CommandError(f"{slug}: tags must be a list of nonempty strings.")
        if entry["external"]:
            link = entry.get("link")
            try:
                parsed = urlsplit(link) if isinstance(link, str) else None
            except ValueError as exc:
                raise CommandError(f"{slug}: invalid external link.") from exc
            if not parsed or parsed.scheme not in {"https", "http"} or not parsed.netloc or len(link) > 200:
                raise CommandError(f"{slug}: link must be an HTTP(S) URL of at most 200 characters.")
            entry["url"] = link
        else:
            entry["url"] = slug
            try:
                entry["body"] = (directory / "content" / f"{slug}.md").read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise CommandError(f"{slug}: cannot read Markdown content: {exc}") from exc
            if not entry["body"].strip():
                raise CommandError(f"{slug}: Markdown content is empty.")
        if entry["url"] in urls:
            raise CommandError(f"{slug}: duplicate card URL {entry['url']}.")
        urls.add(entry["url"])
        thumbnail = thumbnail_directory / f"{slug}.png"
        entry["thumbnail"] = thumbnail if thumbnail.is_file() else None
    return index


class Command(BaseCommand):
    help = "Sync education source content to drafts; preserve live pages and omitted entries."

    def handle(self, *args, **options):
        index = read_index(EDUCATION_CONTENT_DIR, THUMBNAIL_DIR)
        with transaction.atomic():
            self.sync_pages(index)

    def sync_pages(self, index):
        homes = Page.objects.filter(slug="home")
        if homes.count() != 1:
            raise CommandError("Expected exactly one home page; resolve the page tree before syncing.")
        home = homes.get()
        if home.url != "/":
            raise CommandError("The home page must resolve to /.")
        existing = Page.objects.child_of(home).filter(slug=EDUCATION_PAGE_SLUG).first()
        if existing and not isinstance(existing.specific, EducationPage):
            raise CommandError("Existing /education/ is not an EducationPage; migrate its type separately.")
        # Detect incompatible tutorial pages before saving any drafts or images.
        if existing:
            for entry in index:
                if not entry["external"]:
                    child = existing.get_children().filter(slug=entry["slug"]).first()
                    if child and not isinstance(child.specific, TutorialDetailPage):
                        raise CommandError(f"{entry['slug']}: existing child is not a TutorialDetailPage.")
        created = existing is None
        if created:
            page = EducationPage(
                title=EDUCATION_PAGE_TITLE,
                slug=EDUCATION_PAGE_SLUG,
                heading=EDUCATION_PAGE_HEADING,
                summary=EDUCATION_PAGE_DESCRIPTION,
                live=False,
                show_in_menus=False,
            )
            home.add_child(instance=page)
            page.add_breadcrumbs(((EDUCATION_PAGE_TITLE, "/education/"),))
        else:
            page = existing.specific
        for entry in index:
            if entry["external"]:
                continue
            self.sync_tutorial(page, entry)
        if not created:
            page = page.get_latest_revision_as_object()
        changed = update_fields(
            page,
            {
                "title": EDUCATION_PAGE_TITLE,
                "heading": EDUCATION_PAGE_HEADING,
                "summary": EDUCATION_PAGE_DESCRIPTION,
            },
        )
        cards_changed = self.sync_cards(page, index)
        if created or changed or cards_changed:
            page.save_revision()
            self.stdout.write("Saved education index draft.")
        else:
            self.stdout.write("Education index already matches; no revision created.")
        self.stdout.write("No pages published. Preview tutorials and index in Wagtail before publishing.")

    def sync_tutorial(self, parent, entry):
        existing = Page.objects.child_of(parent).filter(slug=entry["slug"]).first()
        created = existing is None
        if created:
            page = TutorialDetailPage(title=entry["title"], slug=entry["slug"], live=False, show_in_menus=False)
            parent.add_child(instance=page)
            page.add_breadcrumbs(((EDUCATION_PAGE_TITLE, "/education/"), (entry["title"], "")))
        else:
            page = existing.specific.get_latest_revision_as_object()
        changed = update_fields(
            page,
            {
                "title": entry["title"],
                "heading": entry["title"],
                "description": entry["description"],
                "body": entry["body"],
            },
        )
        if created or changed:
            page.save_revision()
            self.stdout.write(f"Saved tutorial draft: {entry['slug']}.")

    def sync_cards(self, page, index):
        cards = list(page.cards.all())
        by_url = {}
        for card in cards:
            if card.url in by_url:
                raise CommandError(f"Duplicate existing education card URL: {card.url}")
            by_url[card.url] = card
        changed = False
        ordered = []
        for entry in index:
            card = by_url.pop(entry["url"], None)
            if card is None:
                card = TutorialCard(url=entry["url"])
                changed = True
            changed = (
                update_fields(
                    card,
                    {
                        "title": entry["title"],
                        "summary": entry["description"],
                        "category": entry["category"],
                    },
                )
                or changed
            )
            if sorted(card.tags.names()) != sorted(set(entry["tags"])):
                card.tags.set(entry["tags"])
                changed = True
            # Retain existing thumbnails. Import a supplied thumbnail only when
            # the card has none; media replacement is an explicit editorial task.
            if entry["thumbnail"] and not card.thumbnail_image_id:
                card.thumbnail_image = get_canonical_image(entry["title"], entry["thumbnail"], user=None)
                changed = True
            ordered.append(card)
        # Omission is not deletion: retain cards and child pages not in the index.
        ordered.extend(card for card in cards if card.url in by_url)
        for position, card in enumerate(ordered):
            changed = update_fields(card, {"sort_order": position}) or changed
        if changed:
            page.cards.set(ordered)
        return changed
