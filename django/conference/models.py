from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from conference.validators import MarkdownMinLengthValidator
from core.fields import MarkdownField
from core.models import MemberProfile


class Submission2018(models.Model):
    date_created = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=150, validators=[
        MinLengthValidator(10, message=_('Ensure title has %(limit_value)s characters (it is %(show_value)s).'))
    ], help_text=_('Title of the presentation'))
    abstract = MarkdownField(max_length=750, validators=[
        MarkdownMinLengthValidator(20, message=_('Ensure abstract has %(limit_value)s characters (it is %(show_value)s).'))
    ], help_text=_('Description of the presentation in MarkDown'), blank=False)
    video_url = models.URLField(help_text=_('Link to the video'))
    release_url = models.URLField(help_text=_('Link to the model and/or other content associated with the video'))
    author = models.ForeignKey(MemberProfile, on_delete=models.DO_NOTHING)

    def __str__(self):
        return "'{}' by {}".format(self.title, self.author)
