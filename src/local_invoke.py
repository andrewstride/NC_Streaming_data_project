import argparse

def parse_args(arg_list: list[str] | None = None):
    parser = argparse.ArgumentParser()

    parser.add_argument('query', type=str, nargs='+', help='search query')
    parser.add_argument('-d', type=str, help='enter date from (YYYY-MM-DD)?')
    parser.add_argument('reference', type=str, help='reference')

    args = parser.parse_args(arg_list)
    print(f"{args=}")
    return vars(args)

def main():
    # parse given args / handle malformed request/arg
    # Invoke Lambda with JSON event
    # Handle response
        # print details of results found & added to queue
        # OR 
        # details of error?
    print("oy")
    parse_args()

if __name__ == "__main__":
    main()