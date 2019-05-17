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
Trusted digital repositories for software artifacts provide durable archival services for the digital artifacts and metadata entrusted to them and should adhere to [good repository practices](https://www.coretrustseal.org/why-certification/requirements/) and [software citation principles](https://www.force11.org/software-citation-principles) including durable persistent URLs, offsite backups and disaster recovery processes, tombstone metadata pages for inaccessible digital artifacts, and favoring open data formats.
"""
CONTENT = """
This is not an exhaustive list and consists of DOI or other permanent identifier issuing repositories that we are aware of that accept software artifacts including the [CoMSES Computational Model Library (CML)](https://www.comses.net/codebases/). If you have any comments or changes to make to this list, please feel free to [contact us](/about/contact/).

- [Astrophysics Source Code Library](https://ascl.net)
- [Code Ocean](https://codeocean.com)
- [Community Surface Dynamics Modeling System (CSDMS) Model Repository](https://csdms.colorado.edu/wiki/Model_download_portal)
- [Computational Infrastructure for Geodynamics](https://geodynamics.org/cig/software/)
- [CoMSES Computational Model Library](https://www.comses.net/codebases/)
- [HydroShare](https://hydroshare.org)
- [Open Science Framework](https://osf.io)
- [Zenodo](https://zenodo.org)

"""

class Command(BaseCommand):

    """
    Create CoMSES trusted digital repository landing page and add it as a child to the /resources/ CategoryIndexPage
    """
    def handle(self, *args, **options):
        title = 'Trusted Digital Repositories'
        slug = slugify(title)
        repositories_page = MarkdownPage(title=title, slug=slug)
        resources_page = CategoryIndexPage.objects.get(slug='resources')
        try:
            repositories_page = MarkdownPage.objects.get(title=title, slug=slug)
            repositories_page.get_children().delete()
            repositories_page.refresh_from_db()
        except MarkdownPage.DoesNotExist:
            resources_page.add_child(instance=repositories_page)

        repositories_page.heading = 'Trusted Digital Repositories'
        repositories_page.description = DESCRIPTION
        repositories_page.body = CONTENT
        repositories_page.add_breadcrumbs(
            (('Resources', '/resources/'),
             ('Trusted Repositories', '/resources/trusted-digital-repositories/'),)
        )
        revision = repositories_page.save_revision(user=User.objects.get(pk=3), submitted_for_moderation=False)
        revision.publish()
