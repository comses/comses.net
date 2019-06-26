"""
Initializes CoMSES 2019 virtual conference page
"""

import logging

from django.core.management.base import BaseCommand

from home.models import (ConferenceIndexPage, ConferencePage)

logger = logging.getLogger(__name__)

COMSES_2019_INTRO = """
Welcome to CoMSES 2019!

CoMSES Net is hosting its third virtual conference! We welcome presentations dealing with agent-based modeling of social, ecological and social-ecological systems, as well as methodological issues in the context of agent-based modeling. This conference will occur online and is intended for CoMSES Net members. During the conference, which will take place over three weeks, talks will be available for viewing on the conference website, our Discourse forums. Q&A will also take place online during this period, as participants and other CoMSES members can engage with speakers on our [forum](https://forum.comses.net). We will prioritize talks that cover models that have [made their model code and documentation available](https://www.comses.net/codebases/).

"""

COMSES_2019_CONTENT = """
A virtual conference may not have the same intensity as a face-to-face conference but we expect lively interaction between participants. Our goal in organizing these virtual conferences is to provide low cost opportunities for engaging interaction within the CoMSES Net community. There will be no registration fee for the conference, but you will need to be [registered as a CoMSES member](/accounts/signup/) in order to submit a presentation and interact with the presenters.

If you are interested in minimizing your carbon footprint, improving the state of computational modeling and submitting a video presentation for CoMSES 2019, please do the following:

1. Submit a presentation abstract that includes title of your presentation and a description of your abstract.
2. Record yourselves giving a talk with length no more than 12 minutes. You can film yourself giving a talk, have a narrated slide show, or pursue a more ambitious edited video which combines speaking, slides, animations, or model simulations. It is now possible and relatively easy to record a high quality presentation with [modern video editing software](https://en.wikipedia.org/wiki/List_of_video_editing_software).
3. During the conference, participants may ask you questions, and you will be expected to respond to questions raised by your talk. You will automatically receive emails when users post questions or comments on your presentation. Only registered comses.net members will be able to post questions or comments.
4. During the conference, please take the time to view other presentations and interact with the other speakers. Since the conference runs over a three week period you will be able to view all the sessions! No more are we constrained by parallel sessions with interesting talks.
5. Make sure your comses.net [profile page](/accounts/profile/) is up to date by the time of submission.

__Deadlines__

You can find abstract and video submission instructions at the bottom of this page.

- __Abstract submission : Friday, August 30, 2019__
- __Video submission : Monday, September 30, 2019__


__Video Submission Acceptance Criteria__

 Video submission acceptance is based on the following criteria:

- Maximum length video is 12 minutes (_required_)
- Presentation is in English (_required_)
- Presentation is related to the theme of the conference (_required_)
- Presenter is a CoMSES member at the time of submitting the video with an up-to-date profile page (_required_)
- Presenter has included a link to their model code and documentation and archived it in the comses model library or other digital repository (_recommended_)

In the time between the submission and the start of the conference we will check submissions for eligibility and may contact presenters if adjustments are needed. We will then organize the presentations into sessions for the conference as needed. Thank you for being a part of CoMSES Net, and we look forward to seeing what you all are working on!
"""

COMSES_2019_SUBMISSION_INFO = """
[Submit video presentation](submit).
"""

class Command(BaseCommand):

    """
    Create CoMSES 2019 virtual conference conference landing page
    """
    def build_comses_2019_page(self, conference_index_page):
        comses_2019 = ConferencePage(
            slug='2019',
            start_date='2019-10-7',
            end_date='2019-10-25',
            title='CoMSES 2019',
            introduction=COMSES_2019_INTRO,
            content=COMSES_2019_CONTENT,
            submission_information=COMSES_2019_SUBMISSION_INFO,
            external_url='https://forum.comses.net/c/events/comses-2019',
            submission_deadline='2019-9-30',
        )
        conference_index_page.add_child(instance=comses_2019)

    def handle(self, *args, **options):
        conference_index_title = 'CoMSES Virtual Conferences'
        conference_index_page = ConferenceIndexPage.objects.get(title=conference_index_title)
        self.build_comses_2019_page(conference_index_page)
