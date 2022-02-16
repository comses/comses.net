from core.models import Job, Event
from datetime import datetime, timedelta

from core.serializers import EventSerializer, JobSerializer


class JobFactory:
    def __init__(self, submitter):
        self.submitter = submitter

    def get_default_data(self):
        return {
            "title": "PostDoc in ABM",
            "description": "PostDoc in ABM at ASU",
            "submitter": self.submitter,
        }

    def create(self, **overrides):
        job = self.create_unsaved(**overrides)
        job.save()
        return job

    def create_unsaved(self, **overrides):
        kwargs = self.get_default_data()
        kwargs.update(overrides)
        return Job(**kwargs)

    def data_for_create_request(self, **overrides):
        job = self.create(**overrides)
        return JobSerializer(job).data


class EventFactory:
    def __init__(self, submitter):
        self.submitter = submitter

    def get_default_data(self):
        return {
            "title": "CoMSES Conference",
            "description": "Online Conference",
            "location": "Your computer",
            "submitter": self.submitter,
            "start_date": datetime.now() + timedelta(days=1),
        }

    def create(self, **overrides):
        event = self.create_unsaved(**overrides)
        event.save()
        return event

    def create_unsaved(self, **overrides):
        kwargs = self.get_default_data()
        kwargs.update(**overrides)
        return Event(**kwargs)

    def data_for_create_request(self, **overrides):
        event = self.create(**overrides)
        return EventSerializer(event).data
