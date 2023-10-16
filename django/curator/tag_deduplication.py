import abc
import logging
import os
import re
import enum
from typing import List
import pathlib

import dedupe
from taggit.models import Tag

from curator.models import CanonicalTagMapping, CanonicalTag, TagCluster


class AbstractTagDeduper(abc.ABC):
    # TRAINING_FILE = "curator/clustering_training.json"
    TRAINING_FILE = pathlib.Path("curator", "clustering_training.json")
    FIELDS = [{"field": "name", "type": "String"}]

    def uncertain_pairs(self):
        return self.deduper.uncertain_pairs()

    def mark_pairs(self, pairs, is_distinct: bool):
        labelled_examples = {"match": [], "distinct": []}

        example_key = "distinct" if is_distinct else "match"
        labelled_examples[example_key] = pairs

        self.deduper.mark_pairs(labelled_examples)

    def prepare_training_data(self):
        tags = Tag.objects.all().values()
        data = {row["id"]: row for row in tags}
        return data

    def console_label(self):
        dedupe.console_label(self.deduper)

    def training_file_exists(self) -> bool:
        return self.TRAINING_FILE.exists()

    def remove_training_file(self):
        self.TRAINING_FILE.unlink(missing_ok=True)

    def save_to_training_file(self):
        with self.TRAINING_FILE.open("w") as file:
            self.deduper.write_training(file)


class TagClusterManager:
    def reset():
        TagCluster.objects.all().delete()

    def has_unlabelled_clusters():
        return TagCluster.objects.exists()

    def modify_cluster(tag_cluster: TagCluster):
        action = ""
        while action != "q":
            TagClusterManager.__display_cluster(tag_cluster)
            action = input(
                "What would you like to do?\n(c)hange canonical tag name\n(a)dd tags\n(r)emove tags\n(s)ave\n(f)inish\n"
            )

            if action == "c":
                new_canonical_tag_name = input("What would you like to change it to?\n")
                tag_cluster.canonical_tag_name = new_canonical_tag_name
            elif action == "a":
                tag_name = input("Input the name of the tag you would like to add\n")
                if not tag_cluster.add_tag_by_name(tag_name):
                    print("The tag does not exist in Tags")
            elif action == "r":
                tag_index = input(
                    "Input the number of the tag you would like to remove.\n"
                )

                tags = list(tag_cluster.tags.all())
                if not tag_index.isnumeric() or int(tag_index) >= len(tags):
                    print("Index is out of bounds!")
                    continue

                tags.pop(int(tag_index))
                tag_cluster.tags.set(tags)
            elif action == "s":
                print("Published mapping")
                canonical_tag, tag_mappings = tag_cluster.save_mapping()

                print(
                    f"The following was saved to the database: \n<CanonicalTag {canonical_tag}>\n{tag_mappings}"
                )

            elif action == "f":
                tag_cluster.delete()
                break
            else:
                print("Invalid option!")

    def console_label():
        if not TagCluster.objects.exists():
            logging.info("There aren't any clusters to label.")
            return

        tag_clusters = TagCluster.objects.all()
        for tag_cluster in tag_clusters:
            TagClusterManager.modify_cluster(tag_cluster)

    def console_canonicalize_edit():
        quit = False
        while not quit:
            action = input(
                "What would you like to do?\n(a)dd canonical tag\n(r)emove canonical tag\n(v)iew canonical list\n(m)odify canonical tag\n(q)uit\n"
            )

            if action == "a":
                TagClusterManager.__console_add_new_canonical_tag()
            elif action == "r":
                TagClusterManager.__console_remove_canonical_tag()
            elif action == "v":
                TagClusterManager.__console_view_canonical_tag()
            elif action == "m":
                TagClusterManager.__console_modify_canonical_tag()
            elif action == "q":
                quit = True

    def __console_add_new_canonical_tag():
        new_canonical_tag_name = input("What is your new tag name?\n")
        canonical_tag = CanonicalTag.objects.get_or_create(name=new_canonical_tag_name)
        print("Created:\n", canonical_tag)

    def __console_remove_canonical_tag():
        canonical_tag_name = input("What is the name of the canonical tag to delete?\n")
        canonical_tag = CanonicalTag.objects.filter(name=canonical_tag_name)
        if canonical_tag.exists():
            canonical_tag.delete()
            print("Successfully deleted!")
        else:
            print("Tag not found!")

    def __console_view_canonical_tag():
        canonical_tags = CanonicalTag.objects.all()
        print("Canonical Tag List:")
        for canonical_tag in canonical_tags:
            print(canonical_tag.name)
        print("")

    def __console_modify_canonical_tag():
        name = input("Which one would you like to modify?\n")
        canonical_tag = CanonicalTag.objects.filter(name=name)
        tags = Tag.objects.filter(canonicaltagmapping__canonical_tag=canonical_tag[0])

        if canonical_tag.exists():
            try:
                cluster = TagCluster(
                    canonical_tag_name=canonical_tag[0].name, confidence_score=1
                )
                canonical_tag[0].delete()

                cluster.save()
                cluster.tags.set(tags)
                TagClusterManager.modify_cluster(cluster)
            except KeyboardInterrupt:
                cluster.delete()
                canonical_tag[0].save()
        else:
            print("Canonical tag not found!")

    def __display_cluster(tag_cluster: TagCluster):
        tag_names = [tag.name for tag in tag_cluster.tags.all()]
        print("Canonical tag name:", tag_cluster.canonical_tag_name, end="\n\n")
        print("Tags:")
        for index, tag_name in enumerate(tag_names):
            print(f"{index}. {tag_name}")
        print("")


class TagClusterer(AbstractTagDeduper):
    def __init__(self, clustering_threshold):
        self.clustering_threshold = clustering_threshold

        self.deduper = dedupe.Dedupe(AbstractTagDeduper.FIELDS)
        self.prepare_training()

    # The training data is stored in a file.
    # If it exists, load from the file
    # Otherwise, start from scratch
    def prepare_training(self):
        data = self.prepare_training_data()
        if TagClusterer.TRAINING_FILE.exists():
            with TagClusterer.TRAINING_FILE.open("r") as training_file:
                self.deduper.prepare_training(data, training_file)
        else:
            self.deduper.prepare_training(data)

    # The model is trained and then the data is clustered
    def cluster_tags(self):
        self.deduper.train()
        return self.deduper.partition(
            self.prepare_training_data(), self.clustering_threshold
        )

    # Saves the clusters to the database
    def save_clusters(self, clusters):
        for id_list, confidence_list in clusters:
            tags = Tag.objects.filter(id__in=id_list)
            confidence_score = confidence_list[0]

            tag_cluster = TagCluster(
                canonical_tag_name=tags[0].name, confidence_score=confidence_score
            )
            tag_cluster.save()

            tag_cluster.tags.set(tags)
            tag_cluster.save()

    def save_to_training_file(self):
        with TagClusterer.TRAINING_FILE.open("w") as file:
            self.deduper.write_training(file)

    def training_file_exists(self) -> bool:
        return TagClusterer.TRAINING_FILE.exists()

    def remove_training_file(self):
        TagClusterer.TRAINING_FILE.unlink(missing_ok=True)


class TagGazetteer(AbstractTagDeduper):
    def __init__(self, search_threshold):
        self.search_threshold = search_threshold

        self.deduper = dedupe.Gazetteer(AbstractTagDeduper.FIELDS)
        self.prepare_training()
        self.deduper.train()
        self.deduper.index(self.prepare_canonical_data())

    # The training data is stored in a file.
    # If it exists, load from the file
    # Otherwise, start from scratch
    def prepare_training(self):
        data = self.prepare_training_data()
        canonical_data = self.prepare_canonical_data()

        if self.training_file_exists():
            with TagGazetteer.TRAINING_FILE.open("r") as training_file:
                self.deduper.prepare_training(data, canonical_data, training_file)
        else:
            self.deduper.prepare_training(data, canonical_data)

    def prepare_canonical_data(self):
        tags = CanonicalTag.objects.all().values()
        data = {row["id"]: {**row} for i, row in enumerate(tags)}
        return data

    def search(self, data):
        return self.deduper.search(data, threshold=self.search_threshold)

    # This returns the canonical tag with a name that is most similar to 'name'
    def text_search(self, name: str):
        results = self.search({1: {"id": 1, "name": name}})
        matches = results[0][1]

        matches = [
            (CanonicalTag.objects.filter(pk=match[0])[0], match[1]) for match in matches
        ]

        return matches
