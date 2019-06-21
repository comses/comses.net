"""
Initializes CoMSES virtual conference Page Models and other canned data.
"""

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from home.models import (LandingPage, ConferenceIndexPage, ConferencePage, ConferenceTheme)

logger = logging.getLogger(__name__)

COMSES_2017_INTRO = """
Welcome to the first CoMSES Net virtual conference, CoMSES 2017!

CoMSES, the Network for Computational Modeling in the Social and Ecological Sciences, brings together scholars who
develop and use computational models in the social, environmental, and sustainability sciences. As a member of the NSF
West Big Data Innovation Hub, CoMSES Net is dedicated to fostering open and reproducible scientific computation through
cyberinfrastructure and community development. As the CoMSES community has grown over the years, we continue to actively
explore different ways to engage members and have lined up 18 presentations with topics varying from fisheries to human
migration, and archaeology to business administration. From __October 2nd to October 20th, 2017__ you can engage with
the speakers and other participants in discussions related to these presentations. Most presentations that involve
computational models will have their model code and documentation available so you can dive into the specifics of the
model.
"""

COMSES_2018_INTRO = """
CoMSES Net is hosting its second virtual conference, CoMSES 2018!

We welcome presentations dealing with agent-based modeling of social, ecological and social-ecological systems, as well as methodological issues in the context of agent-based modeling. This conference will occur online and is intended for CoMSES Net members. During the conference, which will take place over three weeks, talks will be available for viewing on the conference website, our Discourse forums. Q&A will also take place online during this period, as participants and other CoMSES members can engage with speakers on our [forum](https://forum.comses.net). We will prioritize talks that cover models that have [made their model code and documentation available](https://www.comses.net/codebases/).
"""

COMSES_2019_INTRO = """
CoMSES Net is hosting its second virtual conference, CoMSES 2019!

We welcome presentations dealing with agent-based modeling of social, ecological and social-ecological systems, as well as methodological issues in the context of agent-based modeling. This conference will occur online and is intended for CoMSES Net members. During the conference, which will take place over three weeks, talks will be available for viewing on the conference website, our Discourse forums. Q&A will also take place online during this period, as participants and other CoMSES members can engage with speakers on our [forum](https://forum.comses.net). We will prioritize talks that cover models that have [made their model code and documentation available](https://www.comses.net/codebases/).

"""

COMSES_2019_CONTENT= """
A virtual conference will probably not have the same intensity as a face-to-face conference, but we expect lively interaction between participants. Our goal in organizing these virtual conferences is to provide low cost opportunities for engaging interaction within the CoMSES Net community. There will be no registration fee for the conference, but you will need to be [registered as a CoMSES member](/accounts/signup/) in order to submit a presentation and/or engage with the presenters.

If you are interested in presenting at CoMSES 2019, instead of traveling to a conference to attend panels and deliver a talk, you will instead be expected to do the following:

1. Record yourselves giving a talk no more than 12 minutes. You can film yourself giving a talk or have a narrated slide show, or pursue a more ambitious edited video which combines speaking, slides, animations, or model simulations. It is now possible and relatively easy to record a high quality presentation with [modern video editing software](https://en.wikipedia.org/wiki/List_of_video_editing_software).
2. During the conference, participants may ask you questions, and you will be expected to respond to questions raised by your talk. You will automatically receive emails when users post questions or comments on your presentation. Only registered comses.net members will be able to post questions or comments.
3. During the conference, you should also view other presentations and ask questions of other speakers. Since the conference is over a three week period you will not experience the problem of many parallel sessions that traditional face-to-face conferences pose.
4. You will be expected to have an up to date [profile page](/accounts/profile/) on comses.net by the time of submission.

The deadline for video submission is __Sunday, September 1__ and we will post a submission link with more information soon. We will decide on acceptance of the video for the conference based on the following criteria:

- Maximum length video is 12 minutes (_required_)
- Presentation is in English (_required_)
- Presentation is related to the theme of the conference (_required_)
- Presenter is a CoMSES member at the time of submitting the video (_required_)
- Presenter has included a link to their model code and documentation and archived it in the comses model library or other digital repository (_recommended_)

In the 2 weeks between the submission and the start of the conference we will check the submissions for eligibility and may contact presenters if adjustments are needed. We will then organize the presentations into sessions for the conference.
"""

COMSES_2019_SUBMISSION_INFO = """
Abstract submission are due by Sunday, September 2019. 
"""

class Command(BaseCommand):

    """
    Create CoMSES virtual conference landing pages, including wagtail replacement for archived CoMSES 2017 page.
    See https://github.com/wagtail/wagtail/issues/742 for more details - this can't be in a data migration because the
    auxiliary methods like add_child aren't available on the migration-frozen wagtail Page instances
    """

    def add_modeling_hdm_panel(self, comses_2017):
        presentations = [
            {
                'title': 'Modeling human behavior in agent-based models of social-ecological systems',
                'url': 'https://forum.comses.net/t/modeling-human-behavior-in-agent-based-models-of-social-ecological-systems/100',
                'user_pk': 2022,
            },
            {
                'title': 'Implications of behavioral change on the social, ecological and economic dimensions of pastoral systems – lessons from an agent-based model',
                'url': 'https://forum.comses.net/t/implications-of-behavioral-change-on-the-social-ecological-and-economic-dimensions-of-pastoral-systems-lessons-from-an-agent-based-model/101',
                'user_pk': 1694,
            },
            {
                'title': 'Formalising fisher diversity in FIBE',
                'url': 'https://forum.comses.net/t/formalising-fisher-diversity-in-fibe/102',
                'user_pk': 514,
            },
            {
                'title': 'Consumats in Lakeland: Exploring the variability in a social-ecological system caused by alternative formalizations of human decision making',
                'url': 'https://forum.comses.net/t/consumats-in-lakeland-exploring-the-variability-in-a-social-ecological-system-caused-by-alternative-formalizations-of-human-decision-making/103',
                'user_pk': 4,
                'contributors': [4, 53],
            },
            {
                'title': 'Modelling human decision making and behaviour in social-ecological systems: practical lessons learned and ways forward',
                'url': 'https://forum.comses.net/t/modelling-human-decision-making-and-behaviour-in-social-ecological-systems-practical-lessons-learned-and-ways-forward/104',
                'user_pk': 1275,
            },
        ]
        panel = ConferenceTheme.objects.create(
            title='Modeling human decision making in social-ecological systems',
            description=('How do we include broad interdisciplinary knowledge on decision making in simple integrated models of humans and '
                         'their environment?'),
            external_url='https://forum.comses.net/t/panel-modeling-human-decision-making-in-social-ecological-systems/83',
            page=comses_2017,
        )
        panel.add_presentations(presentations)

    def add_simulation_archaeology_panel(self, comses_2017):
        presentations = [
            {
                'title': 'Neolithic Agropastoral Expansion: An Evaluation of Theoretical Models Using an Agent-Based Model of the Neolithic Spread in the Western Mediterranean',
                'url': 'https://forum.comses.net/t/95',
                'user_pk': 6,
            },
            {
                'title': 'Experimenting with threshold effects in a multi-resource hunter-gatherer agent-based model',
                'url': 'https://forum.comses.net/t/96',
                'user_pk': 1054,
            },
            {
                'title': 'Studying prehistoric mobility and social networks',
                'url': 'https://forum.comses.net/t/studying-prehistoric-mobility-and-social-networks/97',
                'user_pk': 972,
            },
            {
                'title': 'Placing people in the environment: Coupling agent-based land-use and Earth system models',
                'url': 'https://forum.comses.net/t/placing-people-in-the-environment-coupling-agent-based-land-use-and-earth-system-models/98',
                'user_pk': 1999,
            },
            {
                'title': 'Fire, Humans, and Landscape Change: Simulating Charcoal Proxy Records to explore Anthropogenic Fire and Neolithic Landscapes in the Western Mediterranean',
                'url': 'https://forum.comses.net/t/99',
                'user_pk': 1235,
            },
        ]
        panel = ConferenceTheme.objects.create(
            title='Simulation in Archaeology: New Approaches to Old Questions',
            description='Using agent-based models to rewind the tape and explore mysteries of past human societies.',
            external_url='https://forum.comses.net/t/panel-simulation-in-archaeology-new-approaches-to-old-questions/87',
            page=comses_2017,
        )
        panel.add_presentations(presentations)

    def add_migration_session(self, comses_2017):
        presentations = [
            {
                'title': 'Migration as an adaptive strategy; application to the US-Mexico corridor',
                'url': 'https://forum.comses.net/t/85',
                'user_pk': 1185,
            },
            {
                'title': 'Zero, Some, or Zero-Sum: Exploring Trade-Offs in Identifying Human Trafficking Among Migration Flows',
                'url': 'https://forum.comses.net/t/90',
                'user_pk': 1735,
            }
        ]
        session = ConferenceTheme.objects.create(
            title='Session on Migration',
            category=ConferenceTheme.CATEGORIES.Session,
            description='Breaking boundaries by using agent-based models to derive a deeper understanding human mobility.',
            external_url='https://forum.comses.net/t/session-on-migration/86',
            page=comses_2017,
        )
        session.add_presentations(presentations)

    def add_social_systems_session(self, comses_2017):
        presentations = [
            {
                'title': 'Simulating Macro-Level Effects from Micro-Level Observations: Combining ABM and Lab Experiments',
                'url': 'https://forum.comses.net/t/simulating-macro-level-effects-from-micro-level-observations-combining-abm-and-lab-experiments/94',
                'user_pk': 25,
                'contributors': [1865, 25]
            },
            {
                'title': 'Computational Strategy Formulation for Public Administration: An Agent Based Modeling Case',
                'url': 'https://forum.comses.net/t/computational-strategy-formulation-for-public-administration-an-agent-based-modeling-case/93',
                'user_pk': 1934,
            },
        ]
        session = ConferenceTheme.objects.create(
            title='Session on Social Systems',
            category=ConferenceTheme.CATEGORIES.Session,
            description='On the use of computational models to understand complex social systems.',
            external_url='https://forum.comses.net/t/session-on-social-systems/84',
            page=comses_2017,
        )
        session.add_presentations(presentations)

    def add_fisheries_session(self, comses_2017):
        presentations = [
            {
                'title': 'Spatial and sequential stock depletion through increased fisher mobility: An agent-based modeling approach',
                'url': 'https://forum.comses.net/t/spatial-and-sequential-stock-depletion-through-increased-fisher-mobility-an-agent-based-modeling-approach/91',
                'user_pk': 1932,
            },
            {
                'title': 'A model to simulate underwater visual surveys of fish populations',
                'url': 'https://forum.comses.net/t/a-model-to-simulate-underwater-visual-surveys-of-fish-populations/92',
                'user_pk': 1516,
            }
        ]
        session = ConferenceTheme.objects.create(
            title='Session on Fisheries',
            category=ConferenceTheme.CATEGORIES.Session,
            description='On the not so fish models on fish and fishers.',
            external_url='https://forum.comses.net/t/session-on-fisheries/88',
            page=comses_2017,
        )
        session.add_presentations(presentations)

    def add_model_reuse_session(self, comses_2017):
        presentations = [
            {
                'title': 'Good enough practices for reproducible and reusable computational modeling',
                'url': 'https://forum.comses.net/t/good-enough-practices-for-reproducible-and-reusable-computational-modeling/587',
                'user_pk': 3,
            },
            {
                'title': 'Lessons from implementing in parallel with 3 platforms the same didactic agent-based model ',
                'url': 'https://forum.comses.net/t/lessons-from-implementing-in-parallel-with-3-platforms-the-same-didactic-agent-based-model/106',
                'user_pk': 13,
            },
        ]
        session = ConferenceTheme.objects.create(
            title='Session on Model Reuse',
            category=ConferenceTheme.CATEGORIES.Session,
            description='Lessons on improving the ways we develop, document, and archive our computational models so others can reuse or reproduce our work.',
            external_url='https://forum.comses.net/t/session-on-model-reuse/89',
            page=comses_2017,
        )
        session.add_presentations(presentations)

    def build_comses_2017_page(self, conference_index_page):
        comses_2017 = ConferencePage(
            slug='2017',
            start_date='2017-10-02',
            end_date='2017-10-20',
            title='CoMSES 2017',
            introduction=COMSES_2017_INTRO,
            external_url='https://forum.comses.net/c/events/comses-2017'
        )
        conference_index_page.add_child(instance=comses_2017)
        self.add_modeling_hdm_panel(comses_2017)
        self.add_simulation_archaeology_panel(comses_2017)
        self.add_migration_session(comses_2017)
        self.add_social_systems_session(comses_2017)
        self.add_fisheries_session(comses_2017)
        self.add_model_reuse_session(comses_2017)

    def build_comses_2018_page(self, conference_index_page):
        comses_2018 = ConferencePage(
            slug='2018',
            start_date='2018-10-1',
            end_date='2018-10-19',
            title='CoMSES 2018',
            introduction=COMSES_2018_INTRO,
            # content=COMSES_2018_CONTENT,
            # submission_information=COMSES_2018_SUBMISSION_INFO,
            external_url='https://forum.comses.net/c/events/comses-2018',
            # submission_deadline='2018-9-16',
        )
        conference_index_page.add_child(instance=comses_2018)

    def build_comses_2019_page(self, conference_index_page):
        comses_2019 = ConferencePage(
            slug='2019',
            start_date='2019-10-7',
            end_date='2019-10-25',
            title='CoMSES 2019',
            introduction=COMSES_2019_INTRO,
            content=COMSES_2019_CONTENT,
            submission_information=COMSES_2019_SUBMISSION_INFO,
            external_url='https://forum.comses.net/c/events/comses-2018',
            submission_deadline='2019-9-1',
        )

    def handle(self, *args, **options):
        conference_index_title = 'CoMSES Virtual Conferences'
        conference_index_page = ConferenceIndexPage(title=conference_index_title)
        try:
            cip = ConferenceIndexPage.objects.get(title=conference_index_title)
            cip.get_children().delete()
            cip.refresh_from_db()
            conference_index_page = cip
        except ConferenceIndexPage.DoesNotExist:
            landing_page = LandingPage.objects.first()
            landing_page.add_child(instance=conference_index_page)
            revision = conference_index_page.save_revision(user=User.objects.get(pk=3), submitted_for_moderation=False)
            revision.publish()
        self.build_comses_2017_page(conference_index_page)
        self.build_comses_2018_page(conference_index_page)
        self.build_comses_2019_page(conference_index_page)
