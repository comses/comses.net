"""
Management command to load CoMSES 2017 users JSON dump into the new site
"""

import logging
import pathlib

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.db import models
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import MemberProfile, Institution
from django.core import serializers

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--infile', '-f', help='Input JSON user file')

    def handle(self, *args, **options):
        infile = options['infile']
        path = pathlib.Path(infile)
        if not path.exists():
            raise ValueError("Please enter a valid input file")
        with path.open('r') as data:
            for deserialized_object in serializers.deserialize("json", data):
                obj = deserialized_object.object
                if isinstance(obj, User):
                    user_queryset = User.objects.filter(models.Q(username=obj.username) | models.Q(email=obj.email))
                    user = None
                    if user_queryset.exists():
                        assert user_queryset.count() == 1
                        user = user_queryset.first()
                        user.password = obj.password
                        for attr in ('email', 'username', 'password', 'first_name', 'last_name'):
                            existing_attr = getattr(user, attr)
                            incoming_attr = getattr(obj, attr)
                            if incoming_attr.strip() and existing_attr != incoming_attr:
                                logger.debug("updating %s %s -> %s", attr, existing_attr, incoming_attr)
                                setattr(user, attr, incoming_attr)
                        user.save()
                    else:
                        logger.debug("creating new user %s", obj)
                        obj.pk = None
                        deserialized_object.save()
                        user = User.objects.get(username=obj.username)
                    # create verified EmailAddress for the given user if needed
                    email_address, created = EmailAddress.objects.get_or_create(
                        user=user, email=user.email, verified=True, primary=True)
                    if created:
                        logger.debug("created new email address for user %s", user)
                elif isinstance(obj, SocialAccount):
                    user = User.objects.get(username=obj.user.username)
                    # skip if this social account already exists
                    if not SocialAccount.objects.filter(user=user).exists():
                        obj.pk = None
                        obj.user = user
                        deserialized_object.save()
                        logger.debug("added social account %s", obj)
                elif isinstance(obj, MemberProfile):
                    user = User.objects.get(username=obj.user.username)
                    mpqs = MemberProfile.objects.filter(user=user)
                    if mpqs.exists():
                        # update all memberprofile fields
                        assert mpqs.count() == 1
                        member_profile = mpqs.first()
                        for attr in ('bio', 'degrees', 'institution', 'keywords', 'personal_url', 'professional_url',
                                     'research_interests'):
                            existing_attr = getattr(member_profile, attr)
                            incoming_attr = getattr(obj, attr)
                            if incoming_attr and existing_attr != incoming_attr:
                                setattr(member_profile, attr, incoming_attr)
                        member_profile.save()
                elif isinstance(obj, Institution):
                    if not Institution.objects.filter(name=obj.name).exists():
                        logger.debug("Creating new institution %s", obj)
                        obj.pk = None
                        deserialized_object.save()
                else:
                    logger.debug("unhandled serialized object %s", type(obj))
