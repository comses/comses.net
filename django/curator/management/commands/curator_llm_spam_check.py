import json
import logging
import os
import time

import openstack
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

JETSTREAM_DRY_RUN = False

JETSTREAM_SHELVED_STATUS = "SHELVED_OFFLOADED"
JETSTREAM_ACTIVE_STATUS = "ACTIVE"
JETSTREAM_UNSHELVE_TIMEOUT = 600
JETSTREAM_UNSHELVE_POLLING_INTERVAL = 5
JETSTREAM_SHELVE_TIMEOUT = 900
JETSTREAM_SHELVE_POLLING_INTERVAL = 15

SPAM_CHECK_WORKFLOW_STATUS_TIMEOUT = 3600
SPAM_CHECK_WORKFLOW_STATUS_POLLING_INTERVAL = 5
SPAM_CHECK_API_HEALTHCHECK_TIMEOUT = 300
SPAM_CHECK_API_HEALTHCHECK_INTERVAL = 5
SPAM_CHECK_COMPLETED_STATUS = "COMPLETED"


class APIClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint):
        url = f"{self.base_url}/{endpoint}"
        response = self.session.post(url)
        response.raise_for_status()
        return response.json()


def wait_for_jetstream_server_status(conn, server, target_status, interval, timeout):
    if JETSTREAM_DRY_RUN:
        return True
    else:
        start_time = time.time()
        while time.time() - start_time < timeout:
            server = conn.compute.get_server(server.id)
            if server.status == target_status:
                return True
            time.sleep(interval)
        raise Exception(f"Timeout waiting for server status {target_status}")


def poll_check_spam_workflow_status(api_client, workflow_id, interval, timeout):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            data = api_client.get("status", params={"workflow_id": workflow_id})
            logger.info(
                f"Current status for workflow {workflow_id}: {data.get('status', 'unknown')}"
            )
            if data.get("status") == SPAM_CHECK_COMPLETED_STATUS:
                return True

        except requests.RequestException as e:
            logger.info(f"Error polling server for workflow {workflow_id}: {e}")
        except json.JSONDecodeError as e:
            logger.info(f"Error decoding JSON response for workflow {workflow_id}: {e}")
        time.sleep(interval)
    raise Exception(
        f"Timeout waiting for workflow {workflow_id} status {SPAM_CHECK_COMPLETED_STATUS}"
    )


def poll_check_spam_health_check_status(api_client, interval, timeout):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = api_client.get("ok")
            if response.get("status") == "ok":
                logger.info("API health check passed")
                return True
            else:
                logger.info(f"API health check response: {response}")
        except requests.RequestException as e:
            logger.info(f"API health check failed: {e}")
        time.sleep(interval)
    logger.error("API health check timed out")
    return False


class Command(BaseCommand):
    help = f"Unshelves the JetStream2 instance which starts CheckSpamWorkflow. Polls for workflow status {SPAM_CHECK_COMPLETED_STATUS} then shelves the instance."

    def handle(self, *args, **options):
        # Set environment variables
        os.environ["OS_AUTH_URL"] = "https://js2.jetstream-cloud.org:5000/v3/"
        os.environ["OS_AUTH_TYPE"] = "v3applicationcredential"
        os.environ["OS_IDENTITY_API_VERSION"] = "3"
        os.environ["OS_REGION_NAME"] = "IU"
        os.environ["OS_INTERFACE"] = "public"
        os.environ["OS_APPLICATION_CREDENTIAL_ID"] = (
            settings.LLM_SPAM_CHECK_JETSTREAM_OS_APPLICATION_CREDENTIAL_ID
        )
        os.environ["OS_APPLICATION_CREDENTIAL_SECRET"] = (
            settings.LLM_SPAM_CHECK_JETSTREAM_OS_APPLICATION_CREDENTIAL_SECRET
        )

        # Create the connection
        conn = openstack.connect(cloud="envvars")

        # Connect to OpenStack
        conn = openstack.connect()

        JETSTREAM_SERVER_ID = settings.LLM_SPAM_CHECK_JETSTREAM_SERVER_ID
        SPAM_CHECK_API_URL = settings.LLM_SPAM_CHECK_API_URL

        API_KEY = settings.LLM_SPAM_CHECK_API_KEY

        api_client = APIClient(SPAM_CHECK_API_URL, API_KEY)

        try:
            # Find the jetstream2 server
            server = conn.compute.find_server(JETSTREAM_SERVER_ID)

            if not server:
                raise Exception(f"Server with ID {JETSTREAM_SERVER_ID} not found")

            initial_status = server.status
            logger.info(f"Initial server status: {initial_status}")

            if initial_status == JETSTREAM_SHELVED_STATUS:
                logger.info("Unshelving server...")
                if not JETSTREAM_DRY_RUN:
                    conn.compute.unshelve_server(server)

                if wait_for_jetstream_server_status(
                    conn,
                    server,
                    JETSTREAM_ACTIVE_STATUS,
                    JETSTREAM_UNSHELVE_POLLING_INTERVAL,
                    JETSTREAM_UNSHELVE_TIMEOUT,
                ):
                    logger.info("Server is now active")
            elif initial_status == JETSTREAM_ACTIVE_STATUS:
                logger.info("Server is already active")
            else:
                logger.info(
                    f"Server is in {initial_status} state, waiting for it to become ACTIVE"
                )
                if wait_for_jetstream_server_status(
                    conn,
                    server,
                    JETSTREAM_ACTIVE_STATUS,
                    JETSTREAM_UNSHELVE_POLLING_INTERVAL,
                    JETSTREAM_UNSHELVE_TIMEOUT,
                ):
                    logger.info("Server is now active")

            # Ping healthcheck
            if not poll_check_spam_health_check_status(
                api_client,
                SPAM_CHECK_API_HEALTHCHECK_INTERVAL,
                SPAM_CHECK_API_HEALTHCHECK_TIMEOUT,
            ):
                raise Exception("API health check failed")

            # Trigger CheckSpamWorkflow
            data = api_client.post("process-comses-spam")
            workflow_id = data["workflow_id"]

            if not workflow_id:
                raise Exception("Failed to start workflow!")

            logger.info(f"CheckSpamWorkflow started with workflow_id = {workflow_id}")

            # Poll CheckSpamWorkflow status
            logger.info(
                f"Polling for {SPAM_CHECK_API_URL} for {SPAM_CHECK_COMPLETED_STATUS} status..."
            )
            if poll_check_spam_workflow_status(
                api_client,
                workflow_id,
                SPAM_CHECK_WORKFLOW_STATUS_POLLING_INTERVAL,
                SPAM_CHECK_WORKFLOW_STATUS_TIMEOUT,
            ):

                if JETSTREAM_DRY_RUN:
                    server.status = JETSTREAM_ACTIVE_STATUS
                else:
                    # Check if server is already shelved
                    server = conn.compute.get_server(server.id)

                if server.status != JETSTREAM_SHELVED_STATUS:
                    logger.info("Shelving server...")
                    if not JETSTREAM_DRY_RUN:
                        conn.compute.shelve_server(server)
                    else:
                        server.status = JETSTREAM_SHELVED_STATUS

                    # Wait for server to be shelved
                    if wait_for_jetstream_server_status(
                        conn,
                        server,
                        JETSTREAM_SHELVED_STATUS,
                        JETSTREAM_SHELVE_POLLING_INTERVAL,
                        JETSTREAM_SHELVE_TIMEOUT,
                    ):
                        logger.info("Server is now shelved")
                else:
                    logger.info("Server is already shelved")
            else:
                raise Exception(
                    f"Server did not reach {SPAM_CHECK_COMPLETED_STATUS} status"
                )
        except Exception as e:
            logger.error(f"An error occurred: {e}")
