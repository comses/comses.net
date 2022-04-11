"""
management command to move education page from a community subpage to a top level
page under Home
"""

import logging

from django.core.management.base import BaseCommand

from wagtail.core.models import Page

from home.models import (
    MarkdownPage,
    CategoryIndexPage,
    PlatformIndexPage,
    JournalIndexPage,
)

logger = logging.getLogger(__name__)

RESOURCES_NAVIGATION_LINKS = (
    ("Resources", "/resources/"),
    ("Modeling Frameworks", "/resources/modeling-frameworks/"),
    ("Journals", "/resources/journals/"),
    ("Standards", "/resources/standards/"),
    ("Videos", "https://www.youtube.com/user/comsesnet/playlists"),
    ("Bibliometrics", "https://catalog.comses.net"),
)

EDUCATION_PAGE_DESCRIPTION = """
These CoMSES Net tutorials provide hands-on training in best practices for computational modeling and concrete guidance on tools and techniques to share your work and develop advanced data analysis workflows in accordance with the [FAIR principles for research software](https://doi.org/10.15497/RDA00068).

You must be logged in as a COMSES Net member to access these tutorials and have an up-to-date CoMSES Profile.

Eligible users will receive a certificate of completion and digital badge after successfully completing a tutorial and its accompanying assessment.
"""

EDUCATION_PAGE_BODY = """
# Tutorials

#### [Responsible Practices for Scientific Software](/education/good-practices/)
[This tutorial](/education/good-practices/) provides an introduction to the FAIR principles for research software and concrete practices to help you make your computational models more FAIR.

#### Introduction to Git and GitHub

[Join this GitHub classroom](https://classroom.github.com/a/SF1_14wJ) and complete the assignments to familiarize yourself with Git and GitHub. To join the classroom, click the link and associate your GitHub account with a GitHub classroom student roster entry.

If you are new to Git please download [GitHub Desktop](https://desktop.github.com/) to follow along with the GitHub Classroom assignments. We will use a NetLogo model as an example. You will also need a plain text editor like [Atom](https://atom.io/) or [Visual Studio Code](https://code.visualstudio.com/) to resolve git merge conflicts in NetLogo code as NetLogo will not be able to open those files.

#### Introduction to Containerization

[This tutorial](https://classroom.github.com/a/AIdYi37i) introduces the concept of _containerization_ and provides step-by-step guidance on how to containerize an example NetLogo model with transparency and longevity in mind.

# Team Modeling Examples

#### GitHub Community Model

This urban vulnerability project has been used in several CoMSES Winter Schools. Learn to collaborate with other researchers on GitHub for a computational model of governance and vulnerability in an urban setting.

https://github.com/comses/urban-vulnerability 
"""

GOOD_PRACTICES_DESCRIPTION = """
Responsible practices for developing and publishing FAIR+ computational models in efforts to be more transparent, interoperable, and reusable in our work.
"""

GOOD_PRACTICES_BODY = """
## 1. Tutorial Introduction

[Watch the Tutorial Introduction](https://mediaplus.asu.edu/lti/embedded?id=bf90390a-a917-4992-858a-acff6178ac4e&siteId=61e0606e-415d-4001-8206-ffde48430c64)

Info on Open Code Badge: https://www.comses.net/resources/open-code-badge

## 2. The FAIR Principles

[Watch the FAIR Principles Video](https://mediaplus.asu.edu/lti/embedded?id=03a53683-eae9-4da8-9cac-ec7dfefa73d0&siteId=61e0606e-415d-4001-8206-ffde48430c64)

More information about the FAIR Principles:

- The first publication in 2016: Wilkinson, M. D., Dumontier, M., Aalbersberg, I. J., Appleton, G., Axton, M., Baak, A., ... & Mons, B. (2016). The FAIR Guiding Principles for scientific data management and stewardship. Scientific data, 3(1), 1-9. https://doi.org/10.1038/sdata.2016.18
- Further details about the implementation of FAIR Principles for research software: Lamprecht, A. L., Garcia, L., Kuzak, M., Martinez, C., Arcila, R., Martin Del Pico, E., ... & Capella-Gutierrez, S. (2020). Towards FAIR principles for research software. Data Science, 3(1), 37-59. https://doi.org/10.3233/DS-190026
- Research Data Alliance Working Group to establish FAIR Principles for research software: https://www.rd-alliance.org/group/fair-research-software-fair4rs-wg/outcomes/fair-principles-research-software-fair4rs

## 3. Metadata

[Watch the Video on Metadata](https://mediaplus.asu.edu/lti/embedded?id=e1a89d74-71a3-426c-a760-c883df5e7d61&siteId=61e0606e-415d-4001-8206-ffde48430c64)

CodeMeta website: https://codemeta.github.io/index.html

## 4. Code Management

[Watch the Video on Code Management](https://mediaplus.asu.edu/lti/embedded?id=f79a200f-892f-4512-b20d-eddc32b0e1ed&siteId=61e0606e-415d-4001-8206-ffde48430c64)

## 5. Archiving

[Watch the Video on Archiving Your Code](https://mediaplus.asu.edu/lti/embedded?id=66bfb66e-ba8e-48aa-bc53-7a72b72a0dfd&siteId=61e0606e-415d-4001-8206-ffde48430c64)

## 6. Documentation

[Watch the Video on Model Documentation](https://mediaplus.asu.edu/lti/embedded?id=68c653e7-e780-4bf2-bd28-33771586df1c&siteId=61e0606e-415d-4001-8206-ffde48430c64)

More information about UML: https://www.tutorialspoint.com/uml/index.htm 

More information on the ODD protocol
 
- Grimm, V., Berger, U., Bastiansen, F., Eliassen, S., Ginot, V., Giske, J., Goss-Custard, J., Grand, T., Heinz, S., Huse, G., Huth, A., Jepsen, J. U., Jørgensen, C., Mooij, W. M., Müller, B., Pe'er, G., Piou, C., Railsback, S. F., Robbins, A. M., Robbins, M. M., Rossmanith, E., Rüger, N., Strand, E., Souissi, S., Stillman, R. A., Vabø, R., Visser, U., & DeAngelis, D. L. (2006). A standard protocol for describing individual-based and agent-based models. Ecological Modelling, 198, 115-126. https://doi.org/10.1016/j.ecolmodel.2006.04.023
- Grimm, V., S.F. Railsback, C.E. Vincenot, U. Berger, C. Gallagher, D.L. DeAngelis, B. Edmonds, J. Ge, J. Giske, J. Groeneveld, A.S.A. Johnston, A. Milles, J. Nabe-Nielsen, J. Gareth Polhill, V. Radchuk, M.-S. Rohwäder, R.A. Stillman, J.C. Thiele, and D. Ayllón (2020) The ODD Protocol for Describing Agent-Based and Other Simulation Models: A Second Update to Improve Clarity, Replication, and Structural Realism, Journal of Artificial Societies and Social Simulation 23(2) 7, Doi: 10.18564/jasss.4259 Url: http://jasss.soc.surrey.ac.uk/23/2/7.html

## 7. Licenses

[Watch the Video on Software Licenses](https://mediaplus.asu.edu/lti/embedded?id=61b8db6e-8fec-4b56-8fc3-d98ee7b7a81e&siteId=61e0606e-415d-4001-8206-ffde48430c64)

Resources for Choosing a License

- https://ufal.github.io/public-license-selector/
- https://fossa.com/blog/how-choose-right-open-source-license/
- https://choosealicense.com/
- https://www.gnu.org/licenses/license-recommendations.en.html

## Final Assessment

Once you have finished the above tutorials, please complete the following assessment.

Assessment Companion Model: https://www.comses.net/codebase-release/872baf53-09f9-49f2-a430-2d29f5e3445e/

[Take the final assessment](https://forms.gle/5WjshdE2QXXpRhRh9)

"""


class Command(BaseCommand):

    """
    Move existing Education page from under Resources to a top level Page
    """

    def handle(self, *args, **options):
        education_page = MarkdownPage.objects.get(slug="education")

        home_page = Page.objects.get(slug="home")
        education_page.title = "Educational Resources"
        education_page.heading = "Educational Resources"
        education_page.description = EDUCATION_PAGE_DESCRIPTION
        education_page.body.raw = EDUCATION_PAGE_BODY
        education_page.move(home_page, pos="last-child")
        education_page.breadcrumbs.all().delete()
        education_page.navigation_links.all().delete()
        education_page.add_breadcrumbs((("Educational Resources", ""),))
        # remove education from resources subnavigation links
        resources_page = CategoryIndexPage.objects.get(slug="resources")
        resources_page.replace_navigation_links(RESOURCES_NAVIGATION_LINKS)
        # frameworks
        frameworks_page = PlatformIndexPage.objects.first()
        frameworks_page.replace_navigation_links(RESOURCES_NAVIGATION_LINKS)
        # journals
        journals_page = JournalIndexPage.objects.first()
        journals_page.replace_navigation_links(RESOURCES_NAVIGATION_LINKS)
        # standards
        standards_page = MarkdownPage.objects.get(slug="standards")
        standards_page.replace_navigation_links(RESOURCES_NAVIGATION_LINKS)
        # good practices page
        try:
            good_practices_page = MarkdownPage.objects.get(slug="good-practices")
            good_practices_page.breadcrumbs.all().delete()
        except MarkdownPage.DoesNotExist:
            good_practices_page = MarkdownPage(slug="good-practices")

        good_practices_page.add_breadcrumbs(
            (
                ("Educational Resources", "/education/"),
                ("Good Practices Tutorial", ""),
            )
        )
        good_practices_page.title = "Scientific Software Good Practices"
        good_practices_page.heading = (
            "Responsible Practices for Scientific Software Development"
        )
        good_practices_page.description = GOOD_PRACTICES_DESCRIPTION
        good_practices_page.body.raw = GOOD_PRACTICES_BODY
        if not good_practices_page.is_child_of(education_page):
            education_page.add_child(instance=good_practices_page)

        for page in (
            education_page,
            resources_page,
            frameworks_page,
            journals_page,
            standards_page,
            good_practices_page,
        ):
            page.save()


# add good practices to education
