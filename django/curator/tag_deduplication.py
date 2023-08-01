import abc
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


class TagDeduplication(abc.ABC):
    FIELDS = [{"field": "name", "type": "String"}]

    # Gets the model's most uncertain pairs
    def uncertain_pairs(self):
        return self.deduper.uncertain_pairs()

    # Pairs will be two tags.
    # If the tags refer to the same thing, is_distinct = True
    # Otherwise, is_distinct should be equal to False
    def mark_pairs(self, pairs, is_distinct: bool):
        labelled_examples = {"match": [], "distinct": []}

        if is_distinct:
            labelled_examples["distinct"] = pairs
        else:
            labelled_examples["match"] = pairs

        self.deduper.mark_pairs(labelled_examples)

    def prepare_training_data(self):
        tags = Tag.objects.all().values()
        data = {row["id"]: row for i, row in enumerate(tags)}
        return data

    def console_label(self):
        dedupe.console_label(self.deduper)


# This class is used to help to make the initial canonical list.
# Besides that, there isn't much other use for this.
# If the curator can directly provide a small canonical list, even a small one will do, this class will not be needed.
class TagClustering(TagDeduplication):
    TRAINING_FILE = "curator/clustering_training.json"
    CLUSTERING_THRESHOLD = 0.1

    def __init__(self):
        self.deduper = dedupe.Dedupe(TagDeduplication.FIELDS)
        self.prepare_training()

    # The training data is stored in a file.
    # If it exists, load from the file
    # Otherwise, start from scratch
    def prepare_training(self):
        data = self.prepare_training_data()
        if os.path.exists(TagClustering.TRAINING_FILE):
            with open(TagClustering.TRAINING_FILE, "r") as training_file:
                self.deduper.prepare_training(data, training_file)
        else:
            self.deduper.prepare_training(data)

    # The model is trained and then the data is clustered
    def cluster_tags(self):
        self.deduper.train()
        return self.deduper.partition(
            self.prepare_training_data(), TagClustering.CLUSTERING_THRESHOLD
        )

    def save_to_training_file(self):
        with open(TagClustering.TRAINING_FILE, "w") as file:
            self.deduper.write_training(file)

    # Saves the clusters to the database
    def save_clusters(self, clusters):
        for id_list, confidence_list in clusters:
            first_tag = Tag.objects.filter(id=id_list[0])
            if len(first_tag) == 0:
                continue

            canonical_tag = CanonicalTag.objects.get_or_create(name=first_tag[0].name)
            for index in range(len(id_list)):
                tag = Tag.objects.filter(id=id_list[index])
                confidence = confidence_list[index]
                if len(tag) > 0:
                    tag_canon_mapping = CanonicalTagMapping(
                        tag=tag[0],
                        canonical_tag=canonical_tag[0],
                        confidence_score=confidence,
                    )
                    tag_canon_mapping.save()

    def training_file_exists(self) -> bool:
        return os.path.exists(TagClustering.TRAINING_FILE)

    def remove_training_file(self):
        if os.path.isfile(TagClustering.TRAINING_FILE):
            os.remove(TagClustering.TRAINING_FILE)


class TagGazetteering(TagDeduplication):
    TRAINING_FILE = "curator/gazetteering_training.json"
    SEARCH_THRESHOLD = 0.5

    def __init__(self):
        self.deduper = dedupe.Gazetteer(TagDeduplication.FIELDS)
        self.prepare_training()

    # The training data is stored in a file.
    # If it exists, load from the file
    # Otherwise, start from scratch
    def prepare_training(self):
        data = self.prepare_training_data()
        canonical_data = self.prepare_canonical_data()

        if self.training_file_exists():
            with open(TagGazetteering.TRAINING_FILE, "r") as training_file:
                self.deduper.prepare_training(data, canonical_data, training_file)
        else:
            self.deduper.prepare_training(data, canonical_data)

    def prepare_canonical_data(self):
        tags = CanonicalTag.objects.all().values()
        data = {row["id"]: {**row} for i, row in enumerate(tags)}
        return data

    def search(self, data):
        self.deduper.train()
        self.deduper.index(self.prepare_canonical_data())
        return self.deduper.search(data, threshold=TagGazetteering.SEARCH_THRESHOLD)

    def human_readable_search(self, name: str):
        results = self.search({1: {"id": 1, "name": name}})
        matches = results[0][1]

        matches = [
            str(CanonicalTag.objects.filter(pk=match[0])[0])
            + "\tConfidence: "
            + str(match[1])
            for match in matches
        ]

        return "\n".join(matches)

    def training_file_exists(self) -> bool:
        return os.path.exists(TagGazetteering.TRAINING_FILE)

    def remove_training_file(self):
        if os.path.isfile(TagGazetteering.TRAINING_FILE):
            os.remove(TagGazetteering.TRAINING_FILE)

    def save_to_training_file(self):
        with open(TagGazetteering.TRAINING_FILE, "w") as file:
            self.deduper.write_training(file)
