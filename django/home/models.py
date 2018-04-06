import logging
from datetime import datetime
from textwrap import shorten

import requests
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import models
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase
from wagtail.admin.edit_handlers import (FieldPanel, InlinePanel, PageChooserPanel, MultiFieldPanel,
                                         StreamFieldPanel)
from wagtail.core import blocks
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Page, Orderable
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.search import index
from wagtail.snippets.edit_handlers import SnippetChooserPanel
from wagtail.snippets.models import register_snippet

from core.fields import MarkdownField
from core.models import MemberProfile, Platform, Event, Job
from core.utils import get_canonical_image
from .forms import ContactForm
from library.models import Codebase

logger = logging.getLogger(__name__)

"""
Wagtail Page models and related supporting Models and Settings

"""


class UserMessage(models.Model):
    """
    FIXME: consider removing this class, use email for messaging.
    """
    user = models.ForeignKey(User, related_name='inbox', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='outbox', on_delete=models.CASCADE)
    message = models.CharField(max_length=512)
    date_created = models.DateTimeField(auto_now_add=True)
    read_on = models.DateTimeField(null=True, blank=True)

    def is_read(self):
        return self.read_on is not None


class LinkFields(models.Model):
    """
    Cribbed from github.com/wagtail/wagtaildemo
    """
    link_external = models.URLField("External link", blank=True)
    link_page = models.ForeignKey(
        Page,
        null=True,
        blank=True,
        related_name='+',
        on_delete=models.SET_NULL
    )
    link_codebase = models.ForeignKey(
        'library.Codebase',
        null=True,
        blank=True,
        related_name='+',
        on_delete=models.SET_NULL
    )

    @property
    def link(self):
        if self.link_page:
            return self.link_page.url
        elif self.link_codebase:
            return self.link_codebase.get_absolute_url()
        else:
            return self.link_external

    panels = [
        FieldPanel('link_external'),
        PageChooserPanel('link_page'),
        # figure out how to manually link codebase / events / jobs into FeaturedContentItem
        # CodebaseChooserPanel('link_codebase'),
    ]

    class Meta:
        abstract = True


class CarouselItem(LinkFields):
    image = models.ForeignKey('wagtailimages.Image',
                              null=True,
                              blank=True,
                              on_delete=models.SET_NULL,
                              related_name='+')
    codebase_image = models.ForeignKey('library.CodebaseImage',
                                       null=True,
                                       blank=True,
                                       on_delete=models.SET_NULL,
                                       related_name='+')
    embed_url = models.URLField("Embed URL", blank=True)
    caption = models.CharField(max_length=255)
    summary = models.TextField(max_length=600, blank=True)
    title = models.CharField(max_length=255)
    panels = [
        ImageChooserPanel('image'),
        ImageChooserPanel('codebase_image'),
        FieldPanel('embed_url'),
        FieldPanel('caption'),
        FieldPanel('title'),
        MultiFieldPanel(LinkFields.panels, "Link"),
    ]

    @property
    def featured_image(self):
        if self.image:
            return self.image
        elif self.codebase_image:
            return self.codebase_image
        return None

    class Meta:
        abstract = True


class FeaturedContentItem(Orderable, CarouselItem):
    page = ParentalKey('home.LandingPage', related_name='featured_content_queue')


class LandingPage(Page):
    template = 'home/index.jinja'
    FEATURED_CONTENT_COUNT = 6
    MAX_CALLOUT_ENTRIES = 3
    RECENT_FORUM_ACTIVITY_COUNT = 5

    mission_statement = models.CharField(max_length=512)
    community_statement = models.TextField()

    def get_featured_content(self):
        return self.featured_content_queue.all()[:self.FEATURED_CONTENT_COUNT]

    def get_canned_forum_activity(self):
        random_submitters = User.objects.filter(pk__in=(3, 5, 7, 11, 13, 17))
        return [
            {
                'title': "Generated Forum Topic {}".format(i),
                'submitter_name': random_submitters[i].member_profile.name,
                'submitter_url': random_submitters[i].member_profile.get_absolute_url(),
                'date_created': datetime.now(),
                'url': "https://forum.example.com/topic/{}".format(i),
            }
            for i in range(self.RECENT_FORUM_ACTIVITY_COUNT)
        ]

    def _discourse_username_to_submitter(self, username, topic, topic_title):
        submitter = None
        submitter_url = None
        if username != 'comses':
            try:
                submitter = User.objects.get(username=username)
            except User.DoesNotExist:
                pass
        if submitter is None:
            category_id = topic['category_id']
            logger.debug("category id: %s, topic title: %s, topic: %s", category_id, topic_title, topic)
            # special case lookup for real submitter
            # FIXME: get rid of magic constants
            target_object = None
            if category_id == 6:
                # jobs and appointments
                target_object = Job.objects.filter(title=topic_title).order_by('-date_created').first()
            elif category_id == 7:
                # events
                target_object = Event.objects.filter(title=topic_title).order_by('-date_created').first()
            elif category_id == 8:
                target_object = Codebase.objects.filter(title=topic_title).order_by('-date_created').first()
            if target_object:
                submitter = target_object.submitter
                submitter_url = submitter.member_profile.get_absolute_url()
            else:
                submitter = User.objects.get(username='AnonymousUser')
        return submitter, submitter_url

    def get_recent_forum_activity(self):
        # FIXME: move to dedicated discourse module / api as we integrate more tightly with discourse
        # Discourse API endpoint documented at http://docs.discourse.org/#tag/Topics%2Fpaths%2F~1latest.json%2Fget
        if not settings.DEPLOY_ENVIRONMENT.is_production():
            return self.get_canned_forum_activity()
        # FIXME: refactor and clean up logic, extract to a sensible discourse api
        recent_forum_activity = cache.get('recent_forum_activity')
        if recent_forum_activity:
            return recent_forum_activity
        # transform topics list of dictionaries into web template format with title, submitter, date_created, and url.
        try:
            r = requests.get('{0}/{1}'.format(settings.DISCOURSE_BASE_URL, 'latest.json'),
                             params={'order': 'created', 'sort': 'asc'},
                             timeout=3.0)
            posts_dict = r.json()
            topics = posts_dict['topic_list']['topics']
            recent_forum_activity = []
            for topic in topics[:self.RECENT_FORUM_ACTIVITY_COUNT]:
                topic_title = topic['title']
                topic_url = '{0}/t/{1}/{2}'.format(settings.DISCOURSE_BASE_URL,
                                                   topic['slug'],
                                                   topic['id'])
                # getting back to the original submitter involves some trickery.
                # The Discourse embed Javascript queues up a crawler to hit the given page and parses it for content to use
                # as the initial topic text. However, this topic gets added as a specific Discourse User (`comses`,
                # see https://meta.discourse.org/t/embedding-discourse-comments-via-javascript/31963/150 for more details)
                # and so we won't always have the direct username of the submitter without looking it up by
                # 1. Discourse category_id (6 = jobs & appointments, 7 = events, 8 = codebase)
                # 2. Title (not guaranteed to be unique)

                last_poster_username = topic['last_poster_username']
                submitter, submitter_url = self._discourse_username_to_submitter(last_poster_username,
                                                                                 topic,
                                                                                 topic_title)

                recent_forum_activity.append(
                    {
                        'title': topic_title,
                        'submitter_name': submitter.username,
                        'submitter_url': submitter_url,
                        # FIXME: handle created_at=None gracefully, via default date?
                        'date_created': datetime.strptime(topic.get('created_at'), "%Y-%m-%dT%H:%M:%S.%fZ"),
                        'url': topic_url,
                    }
                )
            cache.set('recent_forum_activity', recent_forum_activity, 3600)
            return recent_forum_activity
        except Exception as e:
            logger.exception(e)
            return []

    def get_latest_jobs(self):
        return Job.objects.order_by('-date_created')[:self.MAX_CALLOUT_ENTRIES]

    def get_upcoming_events(self):
        return Event.objects.upcoming().order_by('start_date')[:self.MAX_CALLOUT_ENTRIES]

    def get_context(self, request, *args, **kwargs):
        context = super(LandingPage, self).get_context(request, *args, **kwargs)
        context['featured_content'] = self.get_featured_content()
        context['recent_forum_activity'] = self.get_recent_forum_activity()
        context['latest_jobs'] = self.get_latest_jobs()
        context['upcoming_events'] = self.get_upcoming_events()
        return context

    content_panels = Page.content_panels + [
        FieldPanel('mission_statement', widget=forms.Textarea),
        FieldPanel('community_statement'),
        InlinePanel('featured_content_queue', label=_('Featured Content')),
    ]


class CategoryIndexItem(Orderable, models.Model):
    page = ParentalKey('home.CategoryIndexPage', related_name='callouts')
    image = models.ForeignKey('wagtailimages.Image',
                              null=True,
                              blank=True,
                              on_delete=models.SET_NULL,
                              related_name='+')
    url = models.CharField("Relative path, absolute path, or URL", max_length=200, blank=True)
    title = models.CharField(max_length=255)
    caption = models.CharField(max_length=600)

    def __str__(self):
        return "{0} {1}".format(self.title, self.url)


class SubnavigationMenu():
    pass


class SubNavigationLink(Orderable, models.Model):
    page = ParentalKey(Page, related_name='navigation_links')
    url = models.CharField("Relative path, absolute path, or full URL", max_length=255)
    title = models.CharField(max_length=128)


class Breadcrumb(Orderable, models.Model):
    page = ParentalKey(Page, related_name='breadcrumbs')
    url = models.CharField("Relative / absolute path or full URL", max_length=255, blank=True)
    title = models.CharField(max_length=255)

    def __str__(self):
        return '{0}: {1}'.format(self.title, self.url)


class NavigationMixin(object):
    def add_breadcrumbs(self, breadcrumb_tuples):
        self._add_tuples(breadcrumb_tuples, Breadcrumb)

    def get_breadcrumbs(self):
        return [
            {'url': item.url, 'text': item.title}
            for item in self.breadcrumbs.all()
        ]

    def _add_tuples(self, tuples, cls):
        related_name = cls._meta.get_field('page').related_query_name()
        related_manager = getattr(self, related_name)
        for idx, (title, url) in enumerate(tuples):
            related_manager.add(
                cls(title=title, url=url, sort_order=idx)
            )

    def add_navigation_links(self, navigation_tuples):
        """
        Takes an ordered list of tuples and adds them as navigation links.
        :param navigation_tuples:
        :return:
        """
        self._add_tuples(navigation_tuples, SubNavigationLink)

    def get_navigation_links(self):
        """
        Returns a nested dict for use by the subnav Jinja2 tag.
        :return:
        """
        return [
            {'url': nav.url, 'text': nav.title, 'active': nav.url.endswith(self.slug + '/')}
            for nav in self.navigation_links.all()
        ]


class CategoryIndexPage(NavigationMixin, Page):
    template = models.CharField(max_length=128, default='home/category_index.jinja')
    heading = models.CharField(max_length=128, help_text=_("Short name to be placed in introduction header."))
    summary = models.CharField(max_length=1000, help_text=_('Summary blurb for this category index page.'))

    def add_callout(self, image_path, title, caption, sort_order=None, user=None, url=''):
        if user is None:
            user = User.objects.get(username='alee')
        _image = get_canonical_image(title=title, path=image_path, user=user)
        self.callouts.add(
            CategoryIndexItem(
                title=title,
                sort_order=sort_order,
                caption=caption,
                image=_image,
                url=url,
            )
        )

    content_panels = Page.content_panels + [
        # don't expose template to web form for now, could wreak havoc
        FieldPanel('heading'),
        FieldPanel('template'),
        FieldPanel('summary', widget=forms.Textarea),
        InlinePanel('callouts', label=_('Captioned Image Callouts')),
        InlinePanel('navigation_links', label=_('Subnavigation Links')),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('summary')
    ]


class StreamPage(Page, NavigationMixin):
    template = models.CharField(max_length=128, default='home/stream_page.jinja')
    date = models.DateField("Post date", default=timezone.now)
    description = models.CharField(max_length=512, blank=True)

    body = StreamField([
        ('heading', blocks.CharBlock(classname='full title')),
        ('paragraph', blocks.RichTextBlock()),
        ('image', ImageChooserBlock()),
        ('url', blocks.URLBlock(required=False))
    ])

    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('description'),
        StreamFieldPanel('body'),
    ]


class MarkdownPage(NavigationMixin, Page):
    template = models.CharField(max_length=128, default='home/markdown_page.jinja')
    heading = models.CharField(max_length=128, blank=True)
    date = models.DateField("Post date", default=timezone.now)
    description = MarkdownField(max_length=512, blank=True)
    body = MarkdownField(blank=True)
    jumbotron = models.BooleanField(
        default=True,
        help_text=_("True if this page should display its title and description in a jumbotron"))

    content_panels = Page.content_panels + [
        FieldPanel('heading'),
        FieldPanel('date'),
        FieldPanel('description'),
        FieldPanel('body'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('date'),
        index.SearchField('description'),
        index.SearchField('body')
    ]


class ContactPage(NavigationMixin, Page):
    template = 'home/about/contact.jinja'
    description = models.CharField(max_length=512, blank=True)

    def serve(self, request):
        if request.method == 'POST':
            form = ContactForm(request=request, data=request.POST)
            if form.is_valid():
                form.save()
                return redirect('home:contact-sent')
        else:
            form = ContactForm(request)

        return render(request, self.template, {
            'page': self,
            'form': form,
        })

    content_panels = Page.content_panels + [
        FieldPanel('description')
    ]


class PlatformSnippetPlacement(Orderable, models.Model):
    page = ParentalKey('home.PlatformIndexPage', related_name='platform_placements')
    platform = models.ForeignKey(Platform, related_name='+', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'platform placement'
        verbose_name_plural = 'platform placements'

    panels = [
        SnippetChooserPanel('platform'),
    ]

    def __str__(self):
        return "Snippet placement for {0}".format(self.platform.name)


class PlatformIndexPage(NavigationMixin, Page):
    template = 'home/resources/platforms.jinja'
    description = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        InlinePanel('platform_placements', label='Platforms'),
    ]

    def get_platforms(self):
        # highlight featured platforms? allow the community to rank them.
        return self.platform_placements.order_by('platform__name').all()

    def get_context(self, request):
        context = super().get_context(request)
        # FIXME: add pagination
        context['platforms'] = self.get_platforms()
        return context


class JournalTag(TaggedItemBase):
    content_object = ParentalKey('home.Journal', related_name='tagged_journals')


@register_snippet
class Journal(index.Indexed, ClusterableModel):
    name = models.CharField(max_length=255)
    url = models.URLField()
    issn = models.CharField(max_length=16, blank=True, help_text=_("Linking ISSN-L for this Journal"))
    description = MarkdownField(max_length=1000)
    tags = TaggableManager(through=JournalTag, blank=True)

    panels = [
        FieldPanel('name'),
        FieldPanel('url'),
        FieldPanel('issn'),
        FieldPanel('description', widget=forms.Textarea),
        FieldPanel('tags'),
    ]

    search_fields = [
        index.SearchField('name'),
        index.SearchField('description'),
        index.SearchField('issn'),
        index.RelatedFields('tags', [
            index.SearchField('name'),
        ]),
    ]

    def __str__(self):
        return "{0} {1} {2}".format(self.name, self.url, self.issn)


class JournalSnippetPlacement(Orderable, models.Model):
    page = ParentalKey('home.JournalIndexPage', related_name='journal_placements')
    journal = models.ForeignKey(Journal, related_name='+', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'journal placement'
        verbose_name_plural = 'journal placements'


class JournalIndexPage(NavigationMixin, Page):
    template = 'home/resources/journals.jinja'
    description = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        InlinePanel('journal_placements', label='Journals'),
    ]


@register_snippet
class FaqEntry(index.Indexed, models.Model):
    FAQ_CATEGORIES = Choices(
        ('abm', _('Agent-based Modeling Questions')),
        ('general', _('General CoMSES Net Questions')),
        ('model-library', _('Computational Model Library Questions')),
    )
    category = models.CharField(max_length=32, choices=FAQ_CATEGORIES, default=FAQ_CATEGORIES.general)
    question = models.CharField(max_length=128, help_text=_("Short question"))
    answer = models.TextField(help_text=_("Markdown formatted answer"))
    date_created = models.DateTimeField(auto_now=True)
    last_modified = models.DateTimeField(auto_now_add=True)
    submitter = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "[{0}] {1} {2}".format(self.category, self.question, shorten(self.answer, 140))


class FaqEntryPlacement(Orderable, models.Model):
    page = ParentalKey('home.FaqPage', related_name='faq_entry_placements')
    faq_entry = models.ForeignKey(FaqEntry, related_name='+', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'faq placement'


class FaqPage(Page, NavigationMixin):
    template = 'home/about/faq.jinja'
    description = models.CharField(max_length=1000)

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        # FIXME: add pagination
        context['faq_entries'] = FaqEntry.objects.all()
        context['faq_categories'] = FaqEntry.FAQ_CATEGORIES
        return context

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        InlinePanel('faq_entry_placements', label='FAQ Entries')
    ]

    search_fields = Page.search_fields + [
        index.RelatedFields('faq_entry_placements', [
            index.SearchField('faq_entry')
        ])
    ]


class PeopleEntryPlacement(Orderable, models.Model):
    CATEGORIES = Choices(
        (1, 'directorate', _('Directorate')),
        (2, 'board', _('Executive Board')),
        (3, 'digest', _('CoMSES Digest Editors')),
        (4, 'staff', _('Staff')),
        (5, 'alumni', _('Executive Board Alumni')),
    )
    page = ParentalKey('home.PeoplePage', related_name='people_entry_placements')
    member_profile = models.ForeignKey('core.MemberProfile', related_name='+', on_delete=models.CASCADE)
    category = models.PositiveIntegerField(choices=CATEGORIES, default=CATEGORIES.board)

    def __str__(self):
        return "{0}: {1} {2}".format(self.sort_order, self.member_profile, self.category)

    class Meta:
        verbose_name = 'people entry placement'


class PeoplePage(Page, NavigationMixin):
    template = 'home/about/people.jinja'
    heading = models.CharField(max_length=64)
    description = models.CharField(max_length=1000, blank=True)

    def add_users(self, category, usernames, offset):
        for idx, username in enumerate(usernames):
            # manually iterate and get MemberProfile to enforce original ordering
            profile = MemberProfile.objects.get(user__username=username)
            self.people_entry_placements.add(
                PeopleEntryPlacement(sort_order=offset + idx,
                                     member_profile=profile,
                                     category=category)
            )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context['people_categories'] = PeopleEntryPlacement.CATEGORIES
        return context

    content_panels = Page.content_panels + [
        FieldPanel('heading'),
        FieldPanel('description'),
        InlinePanel('people_entry_placements', label='People Entries')
    ]


class NewsIndexPage(Page):
    def get_context(self, request):
        context = super(NewsIndexPage, self).get_context(request)
        context['news_entries'] = NewsPage.objects.child_of(self).live()
        return context


class NewsPage(Page):
    body = RichTextField()
    date = models.DateField("Post date")
    feed_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    search_fields = Page.search_fields + [
        index.SearchField('body'),
        index.FilterField('date')
    ]

    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('body', classname="full"),
        InlinePanel('related_links', label="Related links"),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
        ImageChooserPanel('feed_image'),
    ]

    # Parent page / subpage type rules
    parent_page_types = ['home.NewsIndexPage']
    subpage_types = []


class NewsPageRelatedLink(Orderable):
    page = ParentalKey(NewsPage, related_name='related_links')
    name = models.CharField(max_length=255)
    url = models.URLField()

    panels = [
        FieldPanel('name'),
        FieldPanel('url'),
    ]
