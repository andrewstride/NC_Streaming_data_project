import os
import logging
import requests

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
    

    # For each result:
    # Process into dict:

    # webPublicationDate
    # webTitle
    # webUrl
    # reference
    # Convert to JSON and Insert up to 10 messages into SQS
    # (automatically ordered by recent first and 10 per page)

    # Send to SQS queue - POST request? Boto3?

    # return {
    #     'numberOfMessages': x,
    #     'error': "error details if error"
    #     'messages': [
    #         {
    #             "contents of each message": "foo"
    #         },
    #         {
    #             "contents of each message": "bar"
    #         }
    #     ]
    # }


def _env_variables():
    required_vars = ["api_key", "sqs_queue_url"]
    env_vars = {}

    for var in required_vars:
        val = os.environ.get(var)
        if not val:
            raise KeyError(f"Missing environment variable: {var}")
        env_vars[var] = val

    return env_vars["api_key"], env_vars["sqs_queue_url"]


def _build_url(query, api_key, date=None):
    url = f"{BASE_URL}q={query}"
    if date:
        url += f"&from-date={date}"
    return url + f"&api-key={api_key}"

def _parse_results(results):
    output = []
    keys = ["webTitle", "webUrl", "webPublicationDate"]
    for result in results:
        parsed = {}
        for key in keys:
            parsed[key] = result[key]
        output.append(parsed)
    return output

def _fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()['response']['results']
        return data
    except requests.exceptions.HTTPError as e:
        raise e