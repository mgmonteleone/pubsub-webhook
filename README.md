# pubsub-webhook

Convert webhook requests to Pub/Sub messages.

This is a robust Google Cloud Function that takes incoming HTTP POST payloads and forwards them to a Pub/Sub topic. 
It includes enhanced error handling, security features, and production-ready logging. 
It's particularly useful if you want to serve a single webhook on Google Cloud and have it trigger multiple subscribers, 
whether it be Cloud Functions or App Engine applications, or anything else subscribing to the topic.

Currently we use this to recieve Monday.com webhook calls.

![Diagram](pubsub-webhook.svg)

## Requirements

* Google Cloud

## Installation

Set the required environment variables:

**Required:**
* `GCP_PROJECT`: the project in which to deploy the function
* `TOPIC_NAME`: the Pub/Sub topic to which to forward the POST payloads

**Optional:**
* `TOPIC_PROJECT`: the project hosting the Pub/Sub topic; defaults to the same project as the function
* `IP_WHITELIST`: comma-delimited list of IP CIDR ranges from which HTTP POST requests must originate (e.g., `192.168.1.0/24,10.0.0.1/32`); defaults to allowing all requests

### Monday.com Egress Addresses

| CIDR notation   | IP range                      |
|-----------------|-------------------------------|
| 82.115.214.0/24 | 82.115.214.0 - 82.115.214.255 |
| 185.66.202.0/23 | 185.66.202.0 - 185.66.203.255 |
| 185.237.4.0/22  | 185.237.4.0 - 185.237.7.255   |
 
### Create Topic

Create a Cloud Pub/Sub topic:

```bash
gcloud pubsub topics create $TOPIC_NAME
```

### Configure IAM

Create a new service account for use by the Cloud Function:

```bash
gcloud iam service-accounts create webhook
```

Grant permissions to publish to the topic:

```bash
gcloud pubsub topics add-iam-policy-binding $TOPIC_NAME \
    --member "serviceAccount:webhook@${GCP_PROJECT}.iam.gserviceaccount.com" \
    --role roles/pubsub.publisher \
    --project $TOPIC_PROJECT
```

### Deploy
```
# Monday.com egress adresses in envar format
82.115.214.0/24,185.66.202.0/23,185.237.4.0/22,104.30.164.2,104.30.164.5
```
```bash
gcloud beta functions deploy monday-webhook \
     --source . \
     --runtime python311 \
     --entry-point pubsub_webhook \
     --service-account webhook@mythic-tenure-197922.iam.gserviceaccount.com \
     --trigger-http \
     --set-env-vars GCP_PROJECT=<GCP_PROJECT>,TOPIC_NAME=<TOPIC_NAME>,IP_WHITELIST=<IP_WHITELIST> \
     --allow-unauthenticated
```

### Test

Run an integration test against a deployed function:

```bash
make integration
```

Ensure you've set the required environment variables (`GCP_PROJECT` and `TOPIC_NAME`) first.

## Features

### Enhanced Error Handling
- Environment variable validation at startup
- Graceful handling of Pub/Sub publishing failures
- Comprehensive error logging with appropriate HTTP status codes
- Timeout protection for Pub/Sub operations

### Security Features
- Robust IP whitelist validation with CIDR range support
- Proper handling of X-Forwarded-For headers for load-balanced environments
- Secure logging that doesn't expose sensitive request data
- Input validation for IP addresses and network ranges

### Production-Ready Design
- Single Pub/Sub client instance for better performance
- Structured logging with Cloud Logging integration
- Standardized HTTP response handling
- Challenge request support for webhook verification

### Monitoring & Observability
- Comprehensive logging for debugging and monitoring
- Request metadata tracking (without sensitive data)
- Error categorization for better troubleshooting
