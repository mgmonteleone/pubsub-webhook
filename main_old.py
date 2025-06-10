import os
from typing import Optional

# Standard library imports
import logging
from ipaddress import ip_address, ip_network

# Third-party imports
import flask
from flask import Request, jsonify
from google.cloud import pubsub_v1
import google.cloud.logging

# Constants
HTTP_METHOD_NOT_ALLOWED = 'Method not allowed'
HTTP_FORBIDDEN = 'Forbidden'
HTTP_OK = 'OK'
ENV_GCP_PROJECT = 'GCP_PROJECT'
ENV_TOPIC_PROJECT = 'TOPIC_PROJECT'
ENV_TOPIC_NAME = 'TOPIC_NAME'
ENV_IP_WHITELIST = 'IP_WHITELIST'


# Validate required environment variables at startup
def validate_environment():
    missing_vars = []
    for var in [ENV_GCP_PROJECT, ENV_TOPIC_NAME]:
        if var not in os.environ:
            missing_vars.append(var)

    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")


# Initialize logging
try:
    client = google.cloud.logging.Client(project=os.getenv(ENV_GCP_PROJECT))
    client.setup_logging()
except Exception as e:
    logging.warning(f"Failed to initialize cloud logging: {e}")
    logging.basicConfig(level=logging.INFO)

# Initialize the Pub/Sub client once
try:
    publisher = pubsub_v1.PublisherClient()
except Exception as e:
    logging.error(f"Failed to initialize Pub/Sub client: {e}")
    publisher = None


def get_client_ip(req: Request) -> Optional[str]:
    """Extract and return client IP address from request."""
    forwarded_for = req.headers.get('X-Forwarded-For')
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs - take the first one
        return forwarded_for.split(',')[0].strip()
    return req.remote_addr


def whitelist_req(req: Request, ranges: str) -> bool:
    """Check if the request IP is in the whitelist."""
    client_ip = get_client_ip(req)
    if not client_ip:
        logging.warning("No client IP found in request")
        return False

    try:
        client_ip_obj = ip_address(client_ip)
        for r in ranges.split(','):
            try:
                network = ip_network(r.strip())
                if client_ip_obj in network:
                    logging.info(f'IP {client_ip} in whitelist')
                    return True
            except ValueError as e:
                logging.warning(f"Invalid network range: {r}: {e}")

        logging.info(f'IP {client_ip} not in whitelist')
        return False
    except ValueError as e:
        logging.warning(f"Invalid IP address: {client_ip}: {e}")
        return False


def create_response(message: str, status_code: int = 200) -> flask.Response:
    """Create a standardized flask response."""
    return flask.Response(message, status_code)


def pubsub_webhook(req: Request) -> flask.Response:
    """
    Main Cloud Function entrypoint that processes webhook requests and
    forwards them to a Pub/Sub topic.
    """
    # Validate HTTP method
    if req.method != 'POST':
        logging.error(f'Invalid method: {req.method}')
        return create_response(HTTP_METHOD_NOT_ALLOWED, 405)

    # Check IP whitelist if configured
    if ENV_IP_WHITELIST in os.environ:
        if not whitelist_req(req, os.environ[ENV_IP_WHITELIST]):
            client_ip = get_client_ip(req) or 'unknown'
            logging.error(f'IP {client_ip} not in whitelist')
            return create_response(HTTP_FORBIDDEN, 403)

    # Handle challenge requests
    if req.json:
        # Log a summarized version of the JSON rather than the whole payload
        json_keys = list(req.json.keys())
        logging.info(f"Received JSON with keys: {json_keys}")

        if req.json.get('challenge'):
            logging.info(f"Responding to challenge request")
            return jsonify(req.get_json())

    # Log request metadata (without potentially sensitive headers and data)
    client_ip = get_client_ip(req) or 'unknown'
    logging.info(f"Received a request from {client_ip}")

    # Ensure the Pub/Sub client is initialized
    if not publisher:
        logging.error("Pub/Sub client is not initialized")
        return create_response("Internal server error", 500)

    # Get topic information
    try:
        topic_project = os.environ.get(ENV_TOPIC_PROJECT, os.environ[ENV_GCP_PROJECT])
        topic_name = os.environ[ENV_TOPIC_NAME]
        topic_path = f'projects/{topic_project}/topics/{topic_name}'

        # Get request data once
        data = req.get_data()

        # Publish to Pub/Sub
        logging.info(f"Publishing to topic: {topic_path}")
        future = publisher.publish(topic_path, data)

        # Wait for the publish operation to complete
        future.result(timeout=30)  # 30 second timeout

        return create_response(HTTP_OK)
    except KeyError as e:
        logging.error(f"Missing environment variable: {e}")
        return create_response("Configuration error", 500)
    except Exception as e:
        logging.error(f"Error publishing message: {e}")
        return create_response("Failed to process webhook", 500)


# Validate environment on module load
try:
    validate_environment()
except EnvironmentError as e:
    logging.error(f"{e}")