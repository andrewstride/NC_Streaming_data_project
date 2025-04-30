from botocore.exceptions import ClientError
import os
import logging
import requests
import boto3
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BASE_URL = "https://content.guardianapis.com/search?"


def lambda_handler(event, context):
    logger.info("Invoked with event: %s", event)
    # Handle event
    try:
        query = event["q"]
        date = event.get("d", None)
        reference = event["ref"]
    except KeyError as e:
        missing_key = e.args[0]
        logger.error("Missing required event key: %s", missing_key)
        return {
            "statusCode": 400,
            "error": "Bad request",
            "message": f"Missing required event key: {missing_key} - 'q' and 'ref' required",
        }
    # Get ENV vars
    logger.info("Attempting to retrieve environment variables")
    try:
        api_key, sqs_queue_url = _env_variables()
        logger.info("Environment variables retrieved")
    except KeyError as e:
        missing_key = e.args[0]
        logger.error("Missing required environment variable: %s", missing_key)
        return {
            "statusCode": 500,
            "error": "Internal server error",
            "message": f"Missing required environment variable: {missing_key}",
        }

    # Build URL
    url = _build_url(query, api_key, date)
    logger.info("URL built, attempting API call")
    # Collect response from Guardian API
    data = _fetch_data(url)
    # Process results into required format
    message_list = _parse_results(data, reference)
    # Send messages to SQS queue
    sqs_client = _get_sqs_client()
    output = {"statusCode": 200, "messagesSent": 0, "messagesFailed": 0}
    for message in message_list:
        response = _send_to_SQS(message, reference, sqs_client, sqs_queue_url)
        if response:
            output["messagesSent"] += 1
        else:
            output["messagesFailed"] += 1

    output["messages"] = message_list
    return output


def _env_variables():
    required_vars = ["api_key", "sqs_queue_url"]
    env_vars = {}

    for var in required_vars:
        val = os.environ.get(var)
        if not val:
            raise KeyError(f"Missing environment variable: {var}")
        env_vars[var] = val

    return env_vars["api_key"], env_vars["sqs_queue_url"]


def _build_url(query: str, api_key: str, date: str = None) -> str:
    url = f"{BASE_URL}q={query}"
    if date:
        url += f"&from-date={date}"
    return url + f"&api-key={api_key}"


def _fetch_data(url: str) -> list:
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()["response"]["results"]
        logger.info("%s result(s) collected", str(len(data)))
        return data
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP Error while fetching data: %s", str(e))
        raise
    except requests.exceptions.Timeout as e:
        logger.error("Timeout occurred while fetching data: %s", str(e))
        raise
    except Exception as e:
        logger.error("Error while fetching data: %s", f"{e.__class__}: {e}")
        raise


def _parse_results(results: list[dict], reference: str) -> list[dict]:
    """Parse results into format for SQS

    Args:
        results (list[dict])
        reference (str)

    Returns:
        list[dict]: List of formatted messages with reference included
    """
    output = []
    keys = ["webTitle", "webUrl", "webPublicationDate"]
    for result in results:
        parsed = {}
        for key in keys:
            parsed[key] = result[key]
        parsed["reference"] = reference
        output.append(parsed)
    return output


def _get_sqs_client():
    return boto3.client("sqs")


def _send_to_SQS(
    message: dict, reference: str, sqs_client: boto3.client, sqs_queue_url: str
) -> bool:
    """Sends message to SQS queue

    Args:
        message (Dict)
        reference (Str)
        sqs_client (Boto3.client('SQS'))
        sqs_queue_url (Str)

    Returns:
        message_sent (Bool)
    """
    try:
        response = sqs_client.send_message(
            QueueUrl=sqs_queue_url,
            MessageBody=json.dumps(message),
            MessageGroupId=reference,
        )
        logger.info("Message sent. ID: %s", response["MessageId"])
        return bool(response["MessageId"])
    except ClientError as e:
        logger.error("Failed to send message: %s", e.response["Error"]["Message"])
        return False
    except Exception:
        logger.exception("Unexpected error when sending message")
        return False
