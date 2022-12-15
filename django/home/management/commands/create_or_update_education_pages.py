"""
management command to create or update education index page and tutorial detail pages
from markdown formatted files in home/static/education

home/static/education/
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
    CategoryIndexPage,
    EducationPage,
    TutorialDetailPage,
)

logger = logging.getLogger(__name__)

EDUCATION_CONTENT_DIR = "home/static/education/"
EDUCATION_PAGE_SLUG = "education"
EDUCATION_PAGE_TITLE = "Educational Resources"
EDUCATION_PAGE_HEADING = "Training Modules"
EDUCATION_PAGE_DESCRIPTION = """CoMSES Net training modules provide concrete guidance on current best practices for computational modeling and sharing your work in accordance with the [FAIR principles for research software (FAIR4RS)](https://doi.org/10.15497/RDA00068) and [FORCE11 Software Citation Principles](https://doi.org/10.7717/peerj-cs.86).

Our [education forum](https://forum.comses.net/c/education) hosts our [community curated list of additional educational resources](https://forum.comses.net/t/educational-resources/9159/2) and can be used to discuss, collaborate, and share additional educational resources."""


class Command(BaseCommand):

    """
    create or update education index page and tutorial detail pages from markdown formatted files
    """

    def handle(self, *args, **options):
        index = self.load_page_content(EDUCATION_CONTENT_DIR)
        education_page = self.create_or_update_education_page(index)
        self.create_or_update_tut_pages(index, education_page)
        self.update_resources_link()

    def create_or_update_education_page(self, index):
        # delete the old page if it exists
        try:
            education_page = MarkdownPage.objects.get(slug=EDUCATION_PAGE_SLUG)
            education_page.delete()
        except:
            try:
                education_page = EducationPage.objects.get(slug=EDUCATION_PAGE_SLUG)
                education_page.delete()
            except:
                pass
        # create new page
        education_page = EducationPage(slug=EDUCATION_PAGE_SLUG)
        try:
            education_page.breadcrumbs.all().delete()
        except:
            pass
        education_page.add_breadcrumbs(((EDUCATION_PAGE_TITLE, ""),))
        education_page.title = EDUCATION_PAGE_TITLE
        education_page.heading = EDUCATION_PAGE_HEADING
        education_page.summary = EDUCATION_PAGE_DESCRIPTION
        count = 0
        for tut in index:
            education_page.add_card(
                image_path=tut["thumbnail"],
                title=tut["title"],
                summary=tut["description"],
                tags=tut["tags"],
                url=tut["slug"] if not tut["external"] else tut["link"],
                sort_order=count,
            )
            count += 1

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
            file = Path(dir, "thumbnails/", tut["slug"] + ".png")
            if file.is_file():
                tut["thumbnail"] = str(file)
            else:
                tut["thumbnail"] = None
            # get body content if not external link
            if not tut["external"]:
                try:
                    file = Path(dir, "content/", tut["slug"] + ".md")
                    tut["body"] = file.read_text()
                except:
                    logger.fatal("%s markdown file does not exist", tut["slug"])

        return index

    def update_resources_link(self):
        # update link to education page on /resources
        try:
            resources_page = CategoryIndexPage.objects.get(slug="resources")
            education_card = resources_page.callouts.get(title="Education")
            education_card.url = "/{}/".format(EDUCATION_PAGE_SLUG)
            education_card.save()
            logger.info("updated resources link to education page")
        except Exception as e:
            logger.fatal("failed to update resources link to education page")
            logger.debug(e)
            pass
