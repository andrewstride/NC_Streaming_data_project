import argparse
import sys
import json
import os
import boto3
from datetime import datetime
from dotenv import load_dotenv


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
        if args["d"] is None or not _is_valid_date(args["d"]):
            args.pop("d")
        return args
    except Exception as e:
        print(e)
        return None


def _is_valid_date(date: str) -> bool:
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
        if not _is_valid_date(date):
            date = input("Please try again (YYYY-MM-DD): ")

    if _is_valid_date(date):
        print(f"Date: {date}")
    else:
        print("Invalid date. Will not be included")
        date = None

    ref = input("Enter one word reference: ")
    if " " in ref:
        ref = _spaces_replaced(ref)
    print(f"Reference: {ref}")

    args = {"q": query, "ref": ref}

    if date:
        args["d"] = date

    return args


def _spaces_replaced(string):
    output = ""
    for i in range(len(string)):
        if string[i] == " ":
            output += "_"
        else:
            output += string[i]
    return output


def invoke_lambda(lambda_client: boto3.client, lambda_id: str, args: dict) -> dict:
    """Invoke lambda function and return response

    Args:
        lambda_id (str): Lambda name or ARN
        args (dict): {'q': query, ('d': date,) 'ref': ref}

    Returns:
        dict: response
    """

    response = lambda_client.invoke(
        FunctionName=lambda_id,
        InvocationType="RequestResponse",
        LogType="Tail",
        Payload=json.dumps(args)
    )
    return response

def _lambda_name():
    load_dotenv()
    name = os.environ.get('LAMBDA_NAME')
    if not name:
        raise EnvironmentError("LAMBDA_NAME retrieval from .env unsuccessful")
    return name

def main():
    # print details of results found & added to queue
    # OR
    # details of error?
    args = parse_args()
    if not args:
        args = request_args()
    lambda_client = boto3.client('lambda')
    response = invoke_lambda(lambda_client, _lambda_name(), args)
    print(response)
    # TODO: Handle response - details of results added to queue / error



if __name__ == "__main__":
    main()
