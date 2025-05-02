from datetime import datetime
import botocore.client
from dotenv import load_dotenv
import botocore
import argparse
import sys
import json
import os
import boto3


def parse_args(arg_list: list[str] | None = None) -> dict | None:
    """parse given args or sys.args for Search Query, optional Date - YYYY-MM-DD, and Reference

    Args:
        arg_list (list[str] | None, optional): List of strings using flags to declare args: -q query, -d date, -ref reference

    Returns:
        Dict: {"q": query, ("d": date,) "ref": reference} | None
    """

    class Parser(argparse.ArgumentParser):
        def error(self, message):
            self.print_help(sys.stderr)
            raise argparse.ArgumentTypeError(message)

    parser = Parser()

    parser.add_argument("-q", type=str, nargs="+", help="search query")
    parser.add_argument("-d", type=str, help="enter date from (YYYY-MM-DD)?")
    parser.add_argument("-ref", type=str, help="one word reference")
    try:
        args = vars(parser.parse_args(arg_list))
        if args["q"] is None or args["ref"] is None:
            parser.error("-q Query and -ref Reference required")
        for k, v in args.items():
            if isinstance(v, list):
                args[k] = "%20".join([s for s in v])
        if args["d"] is None or not is_valid_date(args["d"]):
            args.pop("d")
        return args
    except Exception as e:
        print(e)


def is_valid_date(date: str) -> bool:
    try:
        return bool(datetime.strptime(date, "%Y-%m-%d"))
    except (ValueError, TypeError):
        return False


def request_args() -> dict:
    """request args through CLI

    Returns:
        dict: {"q": query, ("d": date,) "ref": reference}
    """
    query = input("Enter search query: ")
    print(f"Query: {query}")

    date = None
    if input("Enter date from? (y/n): ") == "y":
        date = input("Enter date (YYYY-MM-DD): ")
        if not is_valid_date(date):
            date = input("Please try again (YYYY-MM-DD): ")

    if is_valid_date(date):
        print(f"Date: {date}")
    else:
        print("Invalid date. Will not be included")
        date = None

    ref = input("Enter one word reference: ")
    if " " in ref:
        ref = spaces_replaced(ref)
    print(f"Reference: {ref}")

    args = {"q": query, "ref": ref}

    if date:
        args["d"] = date

    return args


def spaces_replaced(string):
    output = ""
    for i in range(len(string)):
        if string[i] == " ":
            output += "_"
        else:
            output += string[i]
    return output


def invoke_lambda(
    lambda_client: botocore.client.BaseClient, lambda_id: str, args: dict
) -> dict:
    """Invoke lambda function and return response

    Args:
        lambda_client (BaseClient): A Boto3 Lambda client
        lambda_id (str): Lambda name or ARN
        args (dict): Invocation payload e.g. {'q': query, ('d': date) 'ref': ref}

    Returns:
        dict: response
    """

    try:
        response = lambda_client.invoke(
            FunctionName=lambda_id,
            InvocationType="RequestResponse",
            LogType="Tail",
            Payload=json.dumps(args),
        )
        return response
    except Exception as e:
        print("Error invoking Lambda")
        raise RuntimeError(f"Failed to invoke Lambda: {e}")


def lambda_name() -> str:
    load_dotenv()
    name = os.environ.get("LAMBDA_NAME")
    if not name:
        raise EnvironmentError("LAMBDA_NAME retrieval from .env unsuccessful")
    return name


def get_args():
    args = parse_args()
    if not args:
        args = request_args()
    return args


def handle_lambda_response(response: dict) -> None:
    status_code = response.get("StatusCode")
    if status_code == 200:
        try:
            payload = json.loads(response["Payload"].read())
            if payload["statusCode"] == 200:
                print("Successful response")
                print(f"{payload['messagesSent']} message(s) sent")
                print(f"{payload['messagesFailed']} message(s) failed")
                print("Messages sent:")
                for m in payload["messages"]:
                    print(m)
        except Exception as e:
            print(f"Error handling payload: {e}")
    else:
        print("Invalid Lambda response")
        if status_code:
            print(f"Status Code: {status_code}")
    if response.get("FunctionError"):
        print(f"{response['FunctionError']} Lambda Function Error")


def main():
    args = get_args()
    lambda_client = boto3.client("lambda")
    response = invoke_lambda(lambda_client, lambda_name(), args)
    handle_lambda_response(response)


if __name__ == "__main__":
    main()
