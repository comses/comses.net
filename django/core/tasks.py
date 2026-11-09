import logging

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from huey.contrib.djhuey import db_task

from .models import SpamDetectionSettings
from .spam import SpamDetectionUnavailable, detect_spam

logger = logging.getLogger(__name__)


def queue_spam_check(instance):
    """
    Queue detection only after the content has been committed
    """
    if not SpamDetectionSettings.load().enabled:
        return
    content_type_id = ContentType.objects.get_for_model(type(instance)).id
    # A queue outage must not fail a save that has already committed.
    transaction.on_commit(lambda: check_spam(content_type_id, instance.id), robust=True)


# a minute between retries waits out ASU's per-minute token budget and busy queues
@db_task(retries=3, retry_delay=60)
def check_spam(content_type_id: int, object_id: int):
    """
    Skip completed checks and moderator decisions; retry provider failures
    """
    config = SpamDetectionSettings.load()
    if not config.enabled:
        return
    model = ContentType.objects.get_for_id(content_type_id).model_class()
    instance = model.objects.filter(id=object_id).first()
    if instance is None or not instance.accepts_spam_check():
        return
    content = instance.spam_check_content()
    if instance.spam_moderation and instance.spam_moderation.has_checked(content):
        return
    try:
        check = detect_spam(config, content)
    except SpamDetectionUnavailable:
        logger.warning("skipping spam check for %s: no spam detection model has an API key", instance)
        return
    logger.info(
        "spam check for %s: %s P(spam)=%.3f",
        instance,
        check.detection_method,
        check.detection_details["spam_probability"],
    )
    with transaction.atomic():
        instance = model.objects.select_for_update().filter(id=object_id).first()
        if instance is None or not instance.accepts_spam_check():
            return
        if instance.spam_moderation and instance.spam_moderation.has_checked(content):
            return
        # Retry the initial check if an edit made its result stale.
        if instance.spam_check_content() != content:
            raise RuntimeError("Content changed during spam detection; retry with current content")
        instance.record_spam_check(check.is_spam, check.detection_method, check.detection_details)
