from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from feedgen.feed import FeedGenerator

from core.models import Event

FEED_UPDATE_KEY = 'feed:needs_update'

def add_events(feed_generator):
    events = Event.objects.latest(6)
    for event in events:
        event_entry = feed_generator.add_entry()
        event_entry.id(event.get_absolute_url())
        event_entry.title(event.title)
        event_entry.author({
            'name': event.submitter.get_full_name(),
            'email': event.submitter.email,
            'uri': event.submitter.member_profile.get_absolute_url(),
        })


def should_update_feed():
    return cache.get(FEED_UPDATE_KEY)

def set_update_feed_flag(flag: bool = True):
    cache.set(FEED_UPDATE_KEY, flag, None)

def make_feeds():
    if not should_update_feed():
        return

    all_feed = FeedGenerator()
    all_feed.id('https://www.comses.net/feeds/')
    all_feed.title('CoMSES Net Atom / RSS Feeds')
    all_feed.author({'name': 'comses.net', 'email': settings.SERVER_EMAIL, 'uri': 'https://www.comses.net'})
    all_feed.link(title='CoMSES Net homepage', href='https://www.comses.net', rel='alternate')
    all_feed.link(title='comses net feed', href='https://www.comses.net/feeds/', rel='self')
    all_feed.logo('https://www.comses.net/static/images/comses-openabm-logo.png')
    all_feed.icon('https://www.comses.net/static/images/logo.png')
    all_feed.subtitle('')
    all_feed.language('en')
    now = datetime.now()
    all_feed.updated(now)
    all_feed.copyright('&copy; CoMSES Net 2007 - {0}'.format(now.year))
    add_events(all_feed)
