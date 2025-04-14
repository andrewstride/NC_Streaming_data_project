import argparse


def parse_args(arg_list: list[str] | None = None) -> dict | None:
    """parse given args or sys.args for Search Query, optional Date - YYYY-MM-DD, and Reference

    Args:
        arg_list (list[str] | None, optional): List of strings using flags to declare args: -q query, -d date, -ref reference

    Returns:
        _type_: args Dict | None
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("-q", type=str, nargs="+", help="search query")
    parser.add_argument("-d", type=str, help="enter date from (YYYY-MM-DD)?")
    parser.add_argument("-ref", type=str, help="one word reference")
    try:
        args = vars(parser.parse_args(arg_list))
        if not args["q"] or not args["ref"]:
            raise argparse.ArgumentError("-q Query and -ref Reference required")
        for k, v in args.items():
            if isinstance(v, list):
                args[k] = "%20".join([s for s in v])
        if args["d"] == None:
            args.pop("d")
        return args
    except:
        return None


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
