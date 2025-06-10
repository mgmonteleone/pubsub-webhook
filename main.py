import flask
from google.cloud import pubsub
import os
from flask import Request, jsonify  # Import Request type from Flask
from typing import Tuple, Union
import google.cloud.logging
import logging

client = google.cloud.logging.Client(project=os.getenv('GCP_PROJECT'))
client.setup_logging()



def whitelist_req(req: Request, ranges: str):
    from ipaddress import ip_address, ip_network

    for r in ranges.split(','):
        if ip_address(req.remote_addr) in ip_network(r):
            logging.info(f'Direct IP {req.remote_addr} in whitelist')
            return True
        elif ip_address(req.headers.get('X-Forwarded-For')) in ip_network(r):
            logging.info(f'Forwarded IP {req.headers.get("X-Forwarded-For")} in whitelist')
            return True

    return False

def pubsub_webhook(req: Request) -> Union[str, flask.Response]:
    if req.method != 'POST':
        logging.error(f'Invalid method: {req.method}')
        return flask.Response('Method not allowed', 405)

    if 'IP_WHITELIST' in os.environ:
        if not whitelist_req(req, os.environ['IP_WHITELIST']):
            logging.error(f'Direct IP {req.remote_addr} not in whitelist')
            return (flask.Response('Forbidden', 403))

    if req.json:
        logging.info(f"Received JSON: {req.json}")
        if req.json.get('challenge'):
            logging.info(f"Responding to challenge: {req.json.get('challenge')}")
            return jsonify(req.get_json())

    logging.info(f"Received a request from {req.remote_addr}, {req.headers}, {req.data}")


    client = pubsub.PublisherClient()

    topic_project = os.environ.get('TOPIC_PROJECT', os.environ['GCP_PROJECT'])
    topic_name = os.environ['TOPIC_NAME']

    topic = f'projects/{topic_project}/topics/{topic_name}'
    data = req.get_data()
    logging.info(f"Publishing to topic: {topic}, data was {data.decode('utf-8')}")
    client.publish(topic, req.get_data())
    return 'OK'
