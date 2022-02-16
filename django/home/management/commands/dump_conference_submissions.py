import json

from django.core.management.base import BaseCommand
from django.template.loader import get_template

from home.models import ConferenceSubmission


def create_post(id, author, body, date):
    return {
        "id": id,
        "author": author,
        "body": body,
        "date": date,
    }


def create_topic(id, author, body, date, category, posts):
    return {
        "id": id,
        "author": author,
        "body": body,
        "date": date,
        "category": category,
        "posts": posts,
    }


class Command(BaseCommand):
    help = "Dump conference 2018 submissions to json for ingest into discourse form"

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            dest="category",
            help="discourse category to store the models in",
        )

    def handle(self, *args, **options):
        category = options["category"]
        template = get_template("conference/discourse_submission_body.jinja")

        submissions = ConferenceSubmission.objects.all()
        topics = []
        for submission in submissions:
            body = template.render(
                context=dict(
                    title=submission.title,
                    abstract=submission.abstract,
                    video_url=submission.video_url,
                    release_url=submission.release_url,
                    author=submission.author,
                )
            )
            post = create_post(
                id=1,
                author=submission.author.username,
                body=body,
                date=submission.date_created.isoformat(),
            )
            topic = create_topic(
                id=submission.id,
                author=submission.author.username,
                body=body,
                date=submission.date_created.isoformat(),
                category=category,
                posts=[post],
            )
            topics.append(topic)
        with open("tmp", "w") as f:
            json.dump(topics, f, indent=True)
