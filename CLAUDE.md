# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository contains a Google Cloud Function that converts HTTP webhook requests to Google Cloud Pub/Sub messages. It allows incoming webhook payloads to be forwarded to a Pub/Sub topic, enabling multiple subscribers to react to the same webhook event.

## Commands

### Setup and Development

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r tests/requirements.txt
```

### Testing

```bash
# Run unit tests
make unit
# or
python -m pytest -W ignore::DeprecationWarning -v

# Run integration tests (requires GCP project configuration)
make integration
# or
./tests/integration.sh
```

### Deployment

```bash
# Deploy to Google Cloud Functions
make deploy
# or
./deploy.sh
```

## Architecture

The application consists of a single Google Cloud Function (`pubsub_webhook`) that:

1. Validates required environment variables at startup
2. Receives HTTP POST requests from webhook sources
3. Optionally validates source IP addresses against a whitelist (with enhanced CIDR support)
4. Handles challenge requests (used by some webhook providers for verification)
5. Publishes the request payload to a configured Google Cloud Pub/Sub topic with error handling and timeouts

### Enhanced Features

- **Robust Error Handling**: Comprehensive error handling with proper HTTP status codes and logging
- **Security Improvements**: Enhanced IP validation with X-Forwarded-For header support
- **Performance**: Single Pub/Sub client instance initialization for better performance
- **Monitoring**: Structured logging with Cloud Logging integration and secure request logging
- **Production Ready**: Environment validation, timeout handling, and graceful error recovery

### Key Components

- **main.py**: Contains the Cloud Function implementation
- **deploy.sh**: Script for deploying the function to Google Cloud
- **tests/**: Contains unit tests and an integration test script

### Required Environment Variables

**Required:**
- `GCP_PROJECT`: Google Cloud Project ID
- `TOPIC_NAME`: Pub/Sub topic name

**Optional:**
- `TOPIC_PROJECT`: Project ID for the Pub/Sub topic if different from `GCP_PROJECT`
- `IP_WHITELIST`: Comma-separated list of IP CIDR ranges for IP filtering

The application validates required environment variables at startup and will log an error if they are missing.

## Deployment

The function is deployed as a Google Cloud Function with an HTTP trigger, allowing unauthenticated access. It uses a service account for publishing to Pub/Sub.

## Security

- The function can be restricted to specific IP addresses using the `IP_WHITELIST` environment variable
- The service account used by the function should have only the necessary permissions for Pub/Sub publishing