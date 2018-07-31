from django.test import TestCase
from taggit.models import Tag

from core.serializers import TagSerializer


class TagSerializerTestCase(TestCase):
    def test_name_max_length_check_respected(self):
        too_long = Tag._meta.get_field('name').max_length + 1
        name_too_long = TagSerializer(data={'name': 'a'*too_long})
        self.assertFalse(name_too_long.is_valid())

        valid_name = TagSerializer(data={'name': 'fishing'})
        self.assertTrue(valid_name.is_valid())