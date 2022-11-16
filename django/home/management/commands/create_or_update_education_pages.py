"""
management command to create or update education index page and tutorial detail pages
from markdown formatted files in core/static/education

core/static/education/
|--index.json (list of tutorial)
|--content/
|  |- *.md (markdown formatted files with tutorial body content)
|--thumbnails/
|  |- *.png (thumbnail images for the index page)
"""

import logging
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from wagtail.models import Page

from home.models import (
    MarkdownPage,
    EducationPage,
    TutorialDetailPage,
)

logger = logging.getLogger(__name__)

EDUCATION_CONTENT_DIR = "core/static/education/"
EDUCATION_PAGE_SLUG = "education"
EDUCATION_PAGE_TITLE = "Educational Resources"
EDUCATION_PAGE_HEADING = "Training Modules"
EDUCATION_PAGE_DESCRIPTION = """
These CoMSES Net training modules provide instruction on current best practices for computational modeling with concrete guidance for developing data analysis workflows and sharing your work in accordance with the [FAIR principles for research software](https://doi.org/10.15497/RDA00068).
"""


class Command(BaseCommand):

    """
    create or update education index page and tutorial detail pages from markdown formatted files
    """

    def handle(self, *args, **options):
        index = self.load_page_content(EDUCATION_CONTENT_DIR)
        education_page = self.create_or_update_education_page(index)
        self.create_or_update_tut_pages(index, education_page)

    def create_or_update_education_page(self, index):
        # create or update education page
        try:
            education_page = MarkdownPage.objects.get(slug=EDUCATION_PAGE_SLUG)
            education_page.delete()
        except:
            try:
                education_page = EducationPage.objects.get(slug=EDUCATION_PAGE_SLUG)
            except:
                education_page = EducationPage(slug=EDUCATION_PAGE_SLUG)
                education_page.breadcrumbs.all().delete()

        education_page.add_breadcrumbs(
            ((EDUCATION_PAGE_TITLE, "/{}/".format(EDUCATION_PAGE_SLUG)),)
        )
        education_page.title = EDUCATION_PAGE_TITLE
        education_page.heading = EDUCATION_PAGE_HEADING
        education_page.summary = EDUCATION_PAGE_DESCRIPTION
        for tut in index:
            education_page.add_card(
                image_path=tut["thumbnail"],
                title=tut["title"],
                summary=tut["description"],
                tags=tut["tags"],
                url=tut["slug"] if not tut["external"] else tut["link"],
            )
        home_page = Page.objects.get(slug="home")
        if not education_page.is_child_of(home_page):
            logger.debug(education_page.is_child_of(home_page))
            home_page.add_child(instance=education_page)
        education_page.save()
        return education_page

    def create_or_update_tut_pages(self, index, education_page):
        # create or update tutorial pages
        for tut in index:
            if tut["external"]:
                break
            try:
                tutorial_page = TutorialDetailPage.objects.get(slug=tut["slug"])
                tutorial_page.breadcrumbs.all().delete()
            except TutorialDetailPage.DoesNotExist:
                tutorial_page = TutorialDetailPage(slug=tut["slug"])

            tutorial_page.add_breadcrumbs(
                (
                    (EDUCATION_PAGE_TITLE, "/{}/".format(EDUCATION_PAGE_SLUG)),
                    (tut["title"], ""),
                )
            )
            tutorial_page.title = tut["title"]
            tutorial_page.heading = tut["title"]
            tutorial_page.description = tut["description"]
            tutorial_page.body.raw = tut["body"]
            if not tutorial_page.is_child_of(education_page):
                education_page.add_child(instance=tutorial_page)

            tutorial_page.save()

        education_page.save()

    def load_page_content(self, dir):
        # load index.json
        with Path(dir, "index.json").open(encoding="UTF-8") as source:
            index = json.load(source)
        # load page content from markdown text files
        for tut in index:
            # get image paths
            try:
                file = Path(dir, "thumbnails/", tut["slug"] + ".png")
                tut["thumbnail"] = str(file)
            except:
                tut["thumbnail"] = None
            # get body content if not external link
            if not tut["external"]:
                try:
                    file = Path(dir, "content/", tut["slug"] + ".md")
                    tut["body"] = file.read_text()
                except:
                    logger.fatal("%s markdown file does not exist", tut["slug"])

        return index
