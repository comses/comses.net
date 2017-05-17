import logging
from textwrap import shorten

from django import forms
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase
from wagtail.wagtailadmin.edit_handlers import (FieldPanel, InlinePanel, PageChooserPanel, MultiFieldPanel,
                                                StreamFieldPanel)
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.fields import RichTextField, StreamField
from wagtail.wagtailcore.models import Page, Orderable
from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailsearch import index
from wagtail.wagtailsnippets.edit_handlers import SnippetChooserPanel
from wagtail.wagtailsnippets.models import register_snippet

from core.models import MemberProfile, Platform, Event, Job
from core.utils import get_canonical_image
from home.forms import ContactForm

logger = logging.getLogger(__name__)

"""
Wagtail Page models and related supporting Models and Settings

"""


class UserMessage(models.Model):
    """
    FIXME: consider removing this class, use email for messaging.
    """
    user = models.ForeignKey(User, related_name='inbox')
    sender = models.ForeignKey(User, related_name='outbox')
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
        related_name='+'
    )
    link_codebase = models.ForeignKey(
        'library.Codebase',
        null=True,
        blank=True,
        related_name='+'
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
    embed_url = models.URLField("Embed URL", blank=True)
    caption = models.CharField(max_length=255)
    summary = models.TextField(max_length=600, blank=True)
    title = models.CharField(max_length=255)

    panels = [
        ImageChooserPanel('image'),
        FieldPanel('embed_url'),
        FieldPanel('caption'),
        FieldPanel('title'),
        MultiFieldPanel(LinkFields.panels, "Link"),
    ]

    class Meta:
        abstract = True


class FeaturedContentItem(Orderable, CarouselItem):
    page = ParentalKey('home.LandingPage', related_name='featured_content_queue')


class LandingPage(Page):
    template = 'home/index.jinja'
    FEATURED_CONTENT_COUNT = 6
    MAX_CALLOUT_ENTRIES = 3

    mission_statement = models.CharField(max_length=512)

    def get_featured_content(self):
        return self.featured_content_queue.all()[:self.FEATURED_CONTENT_COUNT]

    def get_recent_forum_activity(self):
        return [
            {
                'title': 'This is a sequence of things that should come from Discourse',
                'submitter': User.objects.first(),
                'date_created': timezone.now(),
                'url': 'https://forum.comses.net',
            },
            {
                'title': 'This is something else that should come from Discourse',
                'submitter': User.objects.first(),
                'date_created': timezone.now(),
                'url': 'https://forum.comses.net',
            },
            {
                'title': 'And another',
                'submitter': User.objects.first(),
                'date_created': timezone.now(),
                'url': 'https://forum.comses.net',
            }
        ]

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
            user = User.objects.first()
        _image = get_canonical_image(path=image_path, title=title, user=user)
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
    description = models.CharField(max_length=512, blank=True)
    body = models.TextField(blank=True)

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

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context['form'] = ContactForm(request=request)
        return context

    content_panels = Page.content_panels + [
        FieldPanel('description')
    ]


class PlatformSnippetPlacement(Orderable, models.Model):
    page = ParentalKey('home.PlatformIndexPage', related_name='platform_placements')
    platform = models.ForeignKey(Platform, related_name='+')

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
        return self.platform_placements.all()

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
    description = models.CharField(max_length=1000)
    tags = TaggableManager(through=JournalTag, blank=True)

    panels = [
        FieldPanel('title'),
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


class JournalSnippetPlacement(Orderable, models.Model):
    page = ParentalKey('home.JournalIndexPage', related_name='journal_placements')
    journal = models.ForeignKey(Journal, related_name='+')

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
    submitter = models.ForeignKey(User, blank=True, null=True)

    def __str__(self):
        return "[{0}] {1} {2}".format(self.category, self.question, shorten(self.answer, 140))


class FaqEntryPlacement(Orderable, models.Model):
    page = ParentalKey('home.FaqPage', related_name='faq_entry_placements')
    faq_entry = models.ForeignKey(FaqEntry, related_name='+')

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
    member_profile = models.ForeignKey('core.MemberProfile', related_name='+')
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


