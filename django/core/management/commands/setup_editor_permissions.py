import logging

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from wagtail.core.models import Page, GroupPagePermission

from core.models import ComsesGroups
from core.utils import confirm

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Assign appropriate permissions to the Editor group to submit changes to the FAQ and Resource pages for
    moderation"""

    CONTENT_TYPE_TUPLES = (
        ("core", "platform"),
        ("home", "faqentry"),
        ("home", "journal"),
    )

    EDITOR_PAGE_SLUGS = ("faq", "resources")

    def handle(self, *args, **options):
        editor_group = ComsesGroups.EDITOR.get_group()
        if confirm("Reset Editors group permissions (y/n)? "):
            editor_group.permissions.clear()
            editor_group.page_permissions.all().delete()

        # special case for wagtail admin access
        wagtail_admin_content_type = ContentType.objects.get(
            app_label="wagtailadmin", model="admin"
        )
        editor_group.permissions.add(
            Permission.objects.get(content_type=wagtail_admin_content_type)
        )

        for app_label, model_name in self.CONTENT_TYPE_TUPLES:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
            for permission in Permission.objects.filter(content_type=ct).exclude(
                codename__startswith="delete"
            ):
                editor_group.permissions.add(permission)

        for page_slug in self.EDITOR_PAGE_SLUGS:
            page = Page.objects.get(slug=page_slug)
            for permission_type in ("add", "edit"):
                GroupPagePermission.objects.create(
                    group=editor_group, page=page, permission_type=permission_type
                )
