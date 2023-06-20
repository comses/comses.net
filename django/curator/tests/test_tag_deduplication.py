import random 
import string

from django.test import TestCase
from taggit.models import Tag

from curator.tag_deduplication import TagPreprocessing, TagClustering, TagGazetteering
from curator.models import CanonicalTag, CanonicalTagMapping


class TagPreprocessingTestCase(TestCase):
    def setUp(self):
        pass

    def test_split_by_and(self):
        preprocessed_Tags = TagPreprocessing.preprocess('biology and chemistry')
        self.assertEqual(['biology', 'chemistry'], preprocessed_Tags, "Failed to split by 'and'")
        self.assertEqual(list, type(preprocessed_Tags))
        
    def test_split_by_semicolon(self):
        preprocessed_Tags = TagPreprocessing.preprocess('agent-based model; land-use')
        self.assertEqual(['agent-based model', 'land-use'], preprocessed_Tags, "Failed to split by ';'")
        self.assertEqual(list, type(preprocessed_Tags))

    def test_split_by_comma(self):
        preprocessed_Tags = TagPreprocessing.preprocess('agent-based model, land-use')
        self.assertEqual(['agent-based model', 'land-use'], preprocessed_Tags, "Failed to split by ','")
        self.assertEqual(list, type(preprocessed_Tags))

class TestTagClustering(TestCase):
    
    def setUp(self):

        for i in range(300): 
            id = TestTagClustering._id_generator()
            CanonicalTag(name=id).save()
            Tag(name=id + "1").save()
            Tag(name=id + "2").save()
            Tag(name=id + "3").save()

    def test_uncertain_pairs(self):
        tag_clustering = TagClustering()
        uncertain_pairs = tag_clustering.uncertain_pairs()
        self.assertEqual(list, type(uncertain_pairs))
        self.assertEqual(1, len(uncertain_pairs))
        self.assertEqual(2, len(uncertain_pairs[0]))
        self.assertEqual(int, type(uncertain_pairs[0][0]['id']))
        self.assertEqual(str, type(uncertain_pairs[0][0]['name']))
        self.assertEqual(str, type(uncertain_pairs[0][0]['slug']))
    
    def test_cluster_tags(self):
        clusters = self._cluster_tags()
        self.assertEqual(list, type(clusters))

        for cluster in clusters:
            self.assertLess(0, len(cluster))
            self.assertLess(0, len(cluster[0]))
            self.assertEqual(1, len(cluster[1]))


    def _cluster_tags(self):
        tag_clustering = TagClustering()
        for i in range(300):
            uncertain_pair = tag_clustering.uncertain_pairs()
            tag_clustering.mark_pairs(uncertain_pair, i % 3 != 0)
        return tag_clustering.cluster_tags()

    def _id_generator(size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))



class TestTagGazetteering(TestCase):
    
    def setUp(self):

        for i in range(300): 
            id = TestTagGazetteering._id_generator()
            CanonicalTag(name=id).save()
            Tag(name=id + "1").save()
            Tag(name=id + "2").save()
            Tag(name=id + "3").save()

    def test_uncertain_pairs(self):
        tag_clustering = TagGazetteering()
        uncertain_pairs = tag_clustering.uncertain_pairs()
        self.assertEqual(list, type(uncertain_pairs))
        self.assertEqual(1, len(uncertain_pairs))
        self.assertEqual(2, len(uncertain_pairs[0]))
        self.assertEqual(int, type(uncertain_pairs[0][0]['id']))
        self.assertEqual(str, type(uncertain_pairs[0][0]['name']))
        self.assertEqual(str, type(uncertain_pairs[0][0]['slug']))
    
    def test_search(self):
        clusters = self._search()
        self.assertEqual(list, type(clusters))

        for cluster in clusters:
            self.assertEqual(int, type(cluster[0]))
            self.assertEqual(tuple, type(cluster[1]))


    def _search(self):
        tag_clustering = TagGazetteering()
        for i in range(300):
            uncertain_pair = tag_clustering.uncertain_pairs()
            tag_clustering.mark_pairs(uncertain_pair, i % 3 != 0)
        return tag_clustering.search({1: {'id': 1, 'name': 'agent-based', 'agent-based': 'agent-based'}})

    def _id_generator(size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

