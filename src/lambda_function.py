import os

def lambda_handler(event, context):
    pass
    # Get ENV variables
    # Build URL
    # Collect response from Guardian API
    # For each result:
        # Process into dict
        # Send to SQS queue


def _env_variables():
    api_key = os.environ.get("api_key")
    sqs_queue_url = os.environ.get("sqs_queue_url")
    return {
        "api_key": api_key,
        "sqs_queue_url": sqs_queue_url
    }

def _build_url(query, reference, api_key, date=None):
    return query + reference + api_key + date