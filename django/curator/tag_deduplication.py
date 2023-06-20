from abc import ABC
import os
import re
from typing import List

import dedupe
from django.utils.text import slugify
from taggit.models import Tag

from curator.models import CanonicalTagMapping, CanonicalTag

class TagPreprocessing:
    def preprocess(tag_name: str) -> List[str]:
        tag_names = re.split(r" and |\;|\,", tag_name)
        tag_names = [tag_name.strip() for tag_name in tag_names]
        return tag_names

class TagDeduplication(ABC):
    TRAINING_FILE = 'curator/training.json'
    SETTINGS_FILE = ''
    FIELDS = [
        {'field': 'name', 'type': 'String'},
        # {'field': 'slug', 'type': 'String'}
    ]

    # Gets the models most uncertain pairs
    def uncertain_pairs(self):
        return self.deduper.uncertain_pairs()
    
    # Pairs will be two tags.
    # If the tags refer to the same thing, is_distinct = True
    # Otherwise, is_distinct should be equal to False
    def mark_pairs(self, pairs, is_distinct: bool):
        labelled_examples = {"match": [], "distinct": []}

        if is_distinct: labelled_examples['distinct'] = pairs
        else: labelled_examples['match'] = pairs

        self.deduper.mark_pairs(labelled_examples)
    
    def prepare_training_data(self):
        tags = Tag.objects.all().values()
        data = {row['id']: row for i, row in enumerate(tags)}
        return data

    def save_to_training_file(self):
        with open(TagClustering.TRAINING_FILE, 'w') as file:
            self.deduper.write_training(file)

# This class is used to help to make the initial canonical list.
# Besides that, there isn't much other use for this. 
# If the curator can directly provide a small canonical list, even a small one will do, this class will not be needed.
class TagClustering(TagDeduplication):

    def __init__(self): 
        self.deduper = dedupe.Dedupe(TagDeduplication.FIELDS)
        self.prepare_training()

    # The training data is stored in a file.
    # If it exists, load from the file
    # Otherwise, start from scratch
    def prepare_training(self):
        data = self.prepare_training_data()
        if os.path.exists(TagClustering.TRAINING_FILE):
            with open(TagClustering.TRAINING_FILE, 'r') as training_file:
                self.deduper.prepare_training(data, training_file)
        else: self.deduper.prepare_training(data)

    # The model is trained and then the data is clustered
    def cluster_tags(self): 
        self.deduper.train()
        return self.deduper.partition(self.prepare_training_data(), 0.5)
    
    # Saves the clusters to the database
    def save_clusters(self, clusters):
        for id_list, confidence_list in clusters:
            first_tag = Tag.objects.filter(id=id_list[0])
            if len(first_tag) == 0: continue 

            canonical_tag = CanonicalTag.objects.get_or_create(name=first_tag[0].name)
            for index in range(len(id_list)):
                tag = Tag.objects.filter(id=id_list[index])
                confidence = confidence_list[index]
                if len(tag) > 0: 
                    tag_canon_mapping = CanonicalTagMapping(tag=tag[0], canonical_tag=canonical_tag[0], confidence_score=confidence)
                    print(tag_canon_mapping)
                    tag_canon_mapping.save()

class TagGazetteering(TagDeduplication):
    def __init__(self):
        self.deduper = dedupe.Gazetteer(TagDeduplication.FIELDS)
        self.prepare_training()
    
    # The training data is stored in a file.
    # If it exists, load from the file
    # Otherwise, start from scratch
    def prepare_training(self):
        data = self.prepare_training_data()
        canonical_data = self.prepare_canonical_data()
        if os.path.exists(TagClustering.TRAINING_FILE):
            with open(TagClustering.TRAINING_FILE, 'r') as training_file:
                self.deduper.prepare_training(data, canonical_data, training_file)
        else: self.deduper.prepare_training(data, canonical_data)

    def prepare_canonical_data(self):
        tags = CanonicalTag.objects.all().values()
        data = {row['id']: {**row, 'slug': str(slugify(row['name']))} for i, row in enumerate(tags)}
        return data

    def search(self, data):
        self.deduper.train()
        self.deduper.index(self.prepare_canonical_data())
        return self.deduper.search(data, threshold=0.5)


# def test():
#     tag_d = TagClustering()

#     for i in range(100):
#         uncertain_pair = tag_d.uncertain_pairs()
#         tag_d.mark_pairs(uncertain_pair, i % 2 == 0)
    
#     clusters = tag_d.cluster_tags()
#     tag_d.save_clusters(clusters=clusters)

#     tag_gaz = TagGazetteering()
#     for i in range(100):
#         uncertain_pair = tag_gaz.uncertain_pairs()
#         try: tag_gaz.mark_pairs(uncertain_pair, i % 2 == 0)
#         except: pass
#     print('SEARCHING')
#     print(tag_gaz.search({1: {'id': 1, 'name': 'agent-based', 'agent-based': 'agent-based'}}))