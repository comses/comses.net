"""
Initializes CoMSES Trusted Digital Repositories Page and other canned data.
"""

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify

from home.models import CategoryIndexPage, MarkdownPage

logger = logging.getLogger(__name__)

DESCRIPTION = """
The Open Code badge is awarded to publications reliant on computational artifacts that archive the source code needed to reproduce their reported results in an open access, trusted digital repository that adheres to best practices for [software citation](https://www.force11.org/software-citation-principles) and [FAIR data](https://www.go-fair.org/fair-principles/).

![open code html](/static/images/icons/open-code-badge-html.png) ![open code terminal](/static/images/icons/open-code-badge-terminal.png)
"""
CONTENT = """
In order to be awarded an Open Code badge, all source code should be made publicly available in a searchable, open access, trusted digital repository. A DOI, permanent URL or other permanent digital resource locator for accessing the model code must be provided that links to the specific version of the code used in the the publication. Narrative documentation and detailed software metadata should also accompany the source code and enable others to fully understand and/or replicate the source code. Metadata should clearly indicate all software, system, and data dependencies needed to compile and/or execute the source code with versions included. 

As a concrete example, model source code made available on an author’s personal website, GitHub repository, or via email request does not meet the criteria for an Open Code badge whereas model source code published in the CoMSES Net Computational Model Library that has also passed the [CoMSES Net peer review process](/reviews/) does. For a comprehensive list of repositories where model source code can be archived to meet Open Code criteria please visit our [trusted digital repositories page](https://www.comses.net/resources/trusted-digital-repositories/).

Journals participating in the Open Code program award Open Code badges to selected publications based on information provided by the authors and reviewers during the submission and review process. Online versions of publications should link the Open Code badge to a permanent digital resource locator that resolves to a landing page for the archived source code. If you have questions on the use of the Open Code badge, please [contact us](/about/contact/)

These badges are derived from the [“Badges to Acknowledge Open Practices” project from the Open Science Framework](https://osf.io/tvyxz/) and are similarly licensed via the [CC-By Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
"""

class Command(BaseCommand):

    """
    Create CoMSES trusted digital repository landing page and add it as a child to the /resources/ CategoryIndexPage
    """
    def handle(self, *args, **options):
        title = 'Open Code Badge'
        slug = slugify(title)
        open_code_page = MarkdownPage(title=title, slug=slug)
        resources_page = CategoryIndexPage.objects.get(slug='resources')
        try:
            open_code_page = MarkdownPage.objects.get(title=title, slug=slug)
            open_code_page.get_children().delete()
            open_code_page.refresh_from_db()
        except MarkdownPage.DoesNotExist:
            resources_page.add_child(instance=open_code_page)

        open_code_page.heading = 'Open Science = Open Code'
        open_code_page.description = DESCRIPTION
        open_code_page.body = CONTENT
        open_code_page.add_breadcrumbs(
            (('Resources', '/resources/'),
             ('Open Code Badge', f'/resources/{slug}'),)
        )
        revision = open_code_page.save_revision(user=User.objects.get(pk=3), submitted_for_moderation=False)
        revision.publish()
