import argparse
import sys
from datetime import datetime


def parse_args(arg_list: list[str] | None = None) -> dict | None:
    """parse given args or sys.args for Search Query, optional Date - YYYY-MM-DD, and Reference

    Args:
        arg_list (list[str] | None, optional): List of strings using flags to declare args: -q query, -d date, -ref reference

    Returns:
        _type_: args Dict | None
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


def main():
    # parse given args / handle malformed request/arg
    # Invoke Lambda with JSON event
    # Handle response
    # print details of results found & added to queue
    # OR
    # details of error?
    parse_args()


if __name__ == "__main__":
    main()
