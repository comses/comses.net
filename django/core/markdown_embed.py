# FIXME: consider moving this elsewhere
import logging

from markdown import Extension
from markdown.inlinepatterns import InlineProcessor
import xml.etree.ElementTree as etree

logger = logging.getLogger(__name__)

PROVIDERS = {
  "youtube": {
    "re": r'youtube\.com/watch\?\S*v=(?P<youtube>[A-Za-z0-9_&=-]+)',
    "embed": "//www.youtube.com/embed/%s"
  },
  "vimeo": {
    "re": r'vimeo\.com/(?P<vimeo>\d+)',
    "embed": "//player.vimeo.com/video/%s"
  }
}

VIDEO_PATTERN = r'\!\[(?P<alt>[^\]]*)\]\((https?://(www\.|)({0}|{1})\S*)' \
                 r'(?<!png)(?<!jpg)(?<!jpeg)(?<!gif)\)'\
                  .format(PROVIDERS["youtube"]["re"], PROVIDERS["vimeo"]["re"])

class VideoEmbedExtension(Extension):
  """
  Embed videos in markdown by using ![alt text](url), supports youtube and vimeo
  """
  def extendMarkdown(self, md):
    link_pattern = VideoEmbedInlineProcessor(VIDEO_PATTERN, md)
    # priority level 175 is arbitrary. there shouldn't be any conflicts with image
    # embeds, but if there are, it can be adjusted
    md.inlinePatterns.register(link_pattern, "video_embed", 175)

class VideoEmbedInlineProcessor(InlineProcessor):
  def handleMatch(self, m, data):
    el = None
    alt = m.group("alt").strip()
    for provider in PROVIDERS.keys():
      video_id = m.group(provider)
      if video_id:
        el = self.create_el(provider, video_id, alt)
    return el, m.start(0), m.end(0)

  def create_el(self, provider, video_id, alt):
    wrapper = etree.Element("div")
    wrapper.set("class", "embed-wrapper embed-responsive embed-responsive-16by9")
    el = etree.Element("iframe")
    el.set("class", provider)
    el.set("src", PROVIDERS[provider]["embed"] % video_id.strip())
    el.set("alt", alt)
    el.set("allowfullscreen", "true")
    wrapper.append(el)
    return wrapper
