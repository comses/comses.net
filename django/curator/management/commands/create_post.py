from django.core.management.base import BaseCommand
from curator.autopost.autopost import autopost_to_bluesky

class Command(BaseCommand):
    help = 'Post a message to Bluesky'

    def add_arguments(self, parser):
        parser.add_argument('message', type=str, help='The message to post on Bluesky')

    def handle(self, *args, **options):
        message = options['message']
        try:
            response = autopost_to_bluesky(message)
            self.stdout.write(self.style.SUCCESS(f"Post created successfully: {response}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error creating post: {e}"))
