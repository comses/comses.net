from huey.contrib.djhuey import db_task


import logging

logger = logging.getLogger(__name__)


@db_task(retries=3, retry_delay=30)
def example_task():
    pass
