import logging
import os
import time
from typing import Callable

import openstack
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)


class Config:
    WORKFLOW_STATUS_COMPLETED = "COMPLETED"
    WORKFLOW_STATUS_TIMEOUT = 3600  # 1 hour
    WORKFLOW_STATUS_POLLING_INTERVAL = 5

    API_HEALTHCHECK_TIMEOUT = 300  # 5 minutes
    API_HEALTHCHECK_INTERVAL = 5

    JETSTREAM_SERVER_STATUS_SHELVED = "SHELVED_OFFLOADED"
    JETSTREAM_SERVER_STATUS_ACTIVE = "ACTIVE"
    JETSTREAM_UNSHELVE_TIMEOUT = 300  # 5 minutes
    JETSTREAM_UNSHELVE_POLLING_INTERVAL = 5
    JETSTREAM_SHELVE_TIMEOUT = 900  # 15 minutes - shelving might take some time due to creation of the instance image.
    JETSTREAM_SHELVE_POLLING_INTERVAL = 15


class SpamCheckException(Exception):
    """Custom exception for spam check related errors."""

    pass


class SpamCheckAPITimeOutException(SpamCheckException):
    pass


class JetStreamTimeOutException(SpamCheckException):
    pass


class SpamCheckAPI:
    """Client for interacting with the spam check API deployed on the JetStream2 instance."""

    def __init__(self, base_url: str, api_key: str):
        if not base_url or not api_key:
            raise ValueError(
                "Both base_url and api_key must be provided for SpamCheckAPI constructor."
            )
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})

    def get(self, endpoint: str, params: dict = None) -> dict:
        return self._request("GET", endpoint, params)

    def post(self, endpoint: str) -> dict:
        return self._request("POST", endpoint)

    def _request(self, method: str, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.request(method, url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise SpamCheckException(f"API request failed: {e}")

    def check_health(self):
        """Polling health check route of the API."""

        def health_check() -> bool:
            try:
                response = self.get("ok")
                if response.get("status") == "ok":
                    logger.info("API health check passed.")
                    return True
                else:
                    logger.info(
                        f"Unexpected API health check response: {response}. Retrying..."
                    )
                    return False
            except Exception as e:
                # need to catch this exception, and retry because the API server might not be ready after the JetStream2 instance has been unshelved
                logger.error(f"Exception during health_check. Retrying...")
                return False

        logger.info(f"Checking SpamCheckAPI...")
        if not _poll_status(
            health_check,
            Config.API_HEALTHCHECK_INTERVAL,
            Config.API_HEALTHCHECK_TIMEOUT,
        ):
            raise SpamCheckAPITimeOutException(
                f"API health check failed to succeed within {Config.API_HEALTHCHECK_TIMEOUT} seconds"
            )

    def start_check_spam_workflow(self) -> str:
        """Start the SpamCheckWorkflow and return the workflow ID."""
        data = self.post("process-comses-spam")
        workflow_id = data["workflow_id"]
        if not workflow_id:
            raise SpamCheckException("No workflow_id in api response!")
        logger.info(f"CheckSpamWorkflow started with workflow_id = {workflow_id}")
        return workflow_id

    def wait_for_workflow_completion(self, workflow_id: str):
        """Wait for the workflow to complete."""
        logger.info(
            f"Polling {self.base_url}/status for {Config.WORKFLOW_STATUS_COMPLETED} status..."
        )

        def check_workflow_completed() -> bool:
            data = self.get("status", params={"workflow_id": workflow_id})
            status = data.get("status", "unknown")
            logger.info(f"Current status for workflow {workflow_id}: {status}")
            return status == Config.WORKFLOW_STATUS_COMPLETED

        if not _poll_status(
            check_workflow_completed,
            Config.WORKFLOW_STATUS_POLLING_INTERVAL,
            Config.WORKFLOW_STATUS_TIMEOUT,
        ):
            raise SpamCheckAPITimeOutException(
                f"Workflow did not reach status {Config.WORKFLOW_STATUS_COMPLETED} within {Config.WORKFLOW_STATUS_TIMEOUT} seconds."
            )


class JetStreamInstanceManager:
    """Manages JetStream2 instance operations."""

    def __init__(self, conn, server_id: str):
        self.conn = conn
        self.server_id = server_id
        self.server = self._find_server()

    def _find_server(self):
        server = self.conn.compute.find_server(self.server_id)
        if not server:
            raise SpamCheckException(f"Server with ID {self.server_id} not found")
        return server

    def ensure_active(self):
        """Ensure the server is in an active state."""
        self.server = self._find_server()
        initial_status = self.server.status
        logger.info(f"Initial server status: {initial_status}")

        if initial_status == Config.JETSTREAM_SERVER_STATUS_SHELVED:
            self._unshelve()
        elif initial_status != Config.JETSTREAM_SERVER_STATUS_ACTIVE:
            self._wait_for_server_status(
                Config.JETSTREAM_SERVER_STATUS_ACTIVE,
                Config.JETSTREAM_UNSHELVE_POLLING_INTERVAL,
                Config.JETSTREAM_UNSHELVE_TIMEOUT,
            )
        else:
            logger.info(
                f"Server status is already {Config.JETSTREAM_SERVER_STATUS_ACTIVE}."
            )

    def shelve(self):
        """Shelve the server if it's not already shelved."""
        self.server = self._find_server()
        if self.server.status != Config.JETSTREAM_SERVER_STATUS_SHELVED:
            logger.info("Shelving server...")
            self.conn.compute.shelve_server(self.server)
            self._wait_for_server_status(
                Config.JETSTREAM_SERVER_STATUS_SHELVED,
                Config.JETSTREAM_SHELVE_POLLING_INTERVAL,
                Config.JETSTREAM_SHELVE_TIMEOUT,
            )
        else:
            logger.info("Server is already shelved")

    def _unshelve(self):
        """Unshelve the server."""
        logger.info("Unshelving server...")
        self.conn.compute.unshelve_server(self.server)
        self._wait_for_server_status(
            Config.JETSTREAM_SERVER_STATUS_ACTIVE,
            Config.JETSTREAM_UNSHELVE_POLLING_INTERVAL,
            Config.JETSTREAM_UNSHELVE_TIMEOUT,
        )

    def _wait_for_server_status(self, target_status: str, interval: int, timeout: int):
        """Wait for the server to reach a specific status."""

        def check_status():
            server = self.conn.compute.get_server(self.server.id)
            is_target_status = server.status == target_status

            if is_target_status:
                logger.info(f"Server has reached {target_status} status.")
            else:
                logger.info(f"Server status is still {server.status}. Retrying...")
            return is_target_status

        if not _poll_status(check_status, interval, timeout):
            raise JetStreamTimeOutException(
                f"Server didn't reach status {target_status} within {timeout} seconds."
            )


def _setup_environment():
    """Set up the environment variables for OpenStack authentication."""
    os.environ.update(
        {
            "OS_AUTH_URL": "https://js2.jetstream-cloud.org:5000/v3/",
            "OS_AUTH_TYPE": "v3applicationcredential",
            "OS_IDENTITY_API_VERSION": "3",
            "OS_REGION_NAME": "IU",
            "OS_INTERFACE": "public",
            "OS_APPLICATION_CREDENTIAL_ID": settings.LLM_SPAM_CHECK_JETSTREAM_OS_APPLICATION_CREDENTIAL_ID,
            "OS_APPLICATION_CREDENTIAL_SECRET": settings.LLM_SPAM_CHECK_JETSTREAM_OS_APPLICATION_CREDENTIAL_SECRET,
        }
    )


def _poll_status(func: Callable[[], bool], interval: int, timeout: int) -> bool:
    """Poll a function until it returns True or timeout is reached."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if func():
            return True
        time.sleep(interval)
    return False


def _run_command(options):
    dry_run = options["skip_changing_instance_state"]
    skip_shelving_when_done = options["skip_shelving_when_done"]

    logger.debug(f"dry_run is {dry_run}")
    logger.debug(f"skip_shelving_when_done is {skip_shelving_when_done}")

    _setup_environment()
    conn = openstack.connect(cloud="envvars")
    jetstream_instance_manager = JetStreamInstanceManager(
        conn, settings.LLM_SPAM_CHECK_JETSTREAM_SERVER_ID
    )

    spam_check_api_client = SpamCheckAPI(
        settings.LLM_SPAM_CHECK_API_URL, settings.LLM_SPAM_CHECK_API_KEY
    )

    if dry_run:
        logger.info(
            f"Mocking server state to be {Config.JETSTREAM_SERVER_STATUS_ACTIVE}"
        )
    else:
        jetstream_instance_manager.ensure_active()

    try:
        spam_check_api_client.check_health()
        workflow_id = spam_check_api_client.start_check_spam_workflow()
        spam_check_api_client.wait_for_workflow_completion(workflow_id)
    except Exception as e:
        logger.error(f"Communication with SpamCheckAPI failed. {e}")
    finally:
        if not skip_shelving_when_done:
            if dry_run:
                logger.info("Mocking shelving server")
            else:
                jetstream_instance_manager.shelve()


class Command(BaseCommand):
    help = f"Unshelve the JetStream2 instance which starts CheckSpamWorkflow. Poll for workflow status {Config.WORKFLOW_STATUS_COMPLETED} then shelve the instance."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-changing-instance-state",
            action="store_true",
            help="Run the command without changing the state of the JetStream2 instance.",
        )
        parser.add_argument(
            "--skip-shelving-when-done",
            action="store_true",
            help="Run the command without shelving the JetStream2 instance after the workflow has completed.",
        )

    def handle(self, *args, **options):
        try:
            _run_command(options)
        except JetStreamTimeOutException as jetstream_timeout_exception:
            # FIXME: send a notification to admin if JetStream2 instance could not be shelved/unshelved! SUs might be burning!
            raise CommandError(
                f"Spam check failed. Check the JetStream2 instance! SUs might be burning! {jetstream_timeout_exception}"
            )
        except Exception as e:
            raise CommandError(f"Spam check failed: {e}")
