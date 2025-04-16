from src.local_invoke import (
    main,
    parse_args,
    _is_valid_date,
    request_args,
    _spaces_replaced,
    invoke_lambda,
    _lambda_name
)
from unittest.mock import patch, Mock
import shlex
import pytest
import os


class TestParseArgs:
    def test_returns_dict(self):
        assert isinstance(parse_args(shlex.split("-q q -ref ref")), dict)

    def test_returns_none_if_no_args(self):
        assert parse_args([]) is None

    def test_returns_dict_with_query_and_reference_keys(self):
        test_input = shlex.split("-q test -r ref")
        output = parse_args(test_input)
        assert list(output.keys()) == ["q", "ref"]

    def test_returns_dict_with_date_key_if_provided(self):
        test_input = shlex.split("-q test -r ref -d 1997-01-01")
        output = parse_args(test_input)
        assert "d" in list(output.keys())

    def test_no_date_given_returns_dict_without_date_key(self):
        test_input = shlex.split("-q test -ref ref")
        output = parse_args(test_input)
        assert "d" not in list(output.keys())

    def test_output_dict_vals_are_strings(self):
        test_input = shlex.split("-q test -ref ref")
        output = parse_args(test_input)
        for v in output.values():
            assert isinstance(v, str)

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            ("-q two words -ref ref", "two%20words"),
            ("-q three word query -ref ref", "three%20word%20query"),
        ],
    )
    def test_joins_multiple_word_query_with_percent_20(self, test_input, expected):
        output = parse_args(shlex.split(test_input))
        assert output["q"] == expected

    expected_dict = {"q": "query", "d": "1997-01-01", "ref": "ref"}

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            ("-q query -ref ref -d 1997-01-01", expected_dict),
            ("-ref ref -q query -d 1997-01-01", expected_dict),
            ("-d 1997-01-01 -ref ref -q query", expected_dict),
        ],
    )
    def test_handles_arg_orders(self, test_input, expected):
        output = parse_args(shlex.split(test_input))
        assert output == expected

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                "-q two words -d 1997-01-01 -ref ref",
                {"q": "two%20words", "d": "1997-01-01", "ref": "ref"},
            ),
            (
                "-q three word query -d 1997-01-01 -ref ref",
                {"q": "three%20word%20query", "d": "1997-01-01", "ref": "ref"},
            ),
        ],
    )
    def test_handles_arg_order_and_multiple_word_query(self, test_input, expected):
        output = parse_args(shlex.split(test_input))
        assert output == expected

    def test_handles_multiple_word_reference(self):
        test_input = shlex.split("-q query -ref three word ref")
        assert parse_args(test_input) is None

    def test_date_not_returned_if_invalid(self):
        test_input = shlex.split("-q test -ref ref -d 123")
        output = parse_args(test_input)
        assert "d" not in list(output.keys())


class TestIsValidDate:
    def test_returns_bool(self):
        assert isinstance(_is_valid_date(""), bool)
        assert isinstance(_is_valid_date("2013-01-02"), bool)
        assert isinstance(_is_valid_date("test"), bool)

    def test_returns_true_for_YYYY_MM_DD_date(self):
        assert _is_valid_date("2001-01-05")
        assert _is_valid_date("1997-12-21")
        assert _is_valid_date("1982-06-28")

    def test_returns_false_for_not_YYYY_MM_DD_string(self):
        assert not _is_valid_date("123-12-12")
        assert not _is_valid_date("test")
        assert not _is_valid_date("2001-23")
        assert not _is_valid_date("1001-10-10-1")

    def test_returns_false_for_month_or_date_out_of_range(self):
        assert not _is_valid_date("2001-13-01")
        assert not _is_valid_date("1997-01-32")

    def test_handles_incorrect_input_format(self):
        assert not _is_valid_date(234)
        assert not _is_valid_date(True)
        assert not _is_valid_date({"test": "dict"})


class TestRequestArgs:
    @patch("src.local_invoke.input")
    def test_query_requested(self, mock_input):
        mock_input.side_effect = ["test", "n", "ref"]
        request_args()
        assert mock_input.call_args_list[0].args[0] == "Enter search query: "

    @patch("src.local_invoke.input")
    def test_query_printed(self, mock_input, capsys):
        mock_input.side_effect = ["test", "y", "1997-01-0", "1997-01-01", "test_ref"]
        request_args()
        captured = capsys.readouterr().out.split("\n")
        assert captured[0] == "Query: test"

    @patch("src.local_invoke.input")
    def test_date_option_given(self, mock_input):
        mock_input.side_effect = ["test", "n", "ref"]
        request_args()
        assert mock_input.call_args_list[1].args[0] == "Enter date from? (y/n): "

    @patch("src.local_invoke.input")
    def test_requests_date_upon_y_input(self, mock_input):
        mock_input.side_effect = ["test", "y", "1997-01-01", "test_ref"]
        request_args()
        assert mock_input.call_args_list[2].args[0] == "Enter date (YYYY-MM-DD): "

    @patch("src.local_invoke.input")
    def test_prompts_again_if_date_incorrect(self, mock_input):
        mock_input.side_effect = ["test", "y", "1997-01-0", "1997-01-01", "test_ref"]
        request_args()
        assert mock_input.call_args_list[3].args[0] == "Please try again (YYYY-MM-DD): "

    @patch("src.local_invoke.input")
    def test_prints_date_if_valid(self, mock_input, capsys):
        mock_input.side_effect = ["test", "y", "1997-01-0", "1997-01-01", "test_ref"]
        request_args()
        captured = capsys.readouterr().out.split("\n")
        assert captured[1] == "Date: 1997-01-01"

    @patch("src.local_invoke.input")
    def test_prints_invalid_date_if_invalid(self, mock_input, capsys):
        mock_input.side_effect = ["test", "y", "1997-01-0", "1997-01-", "test_ref"]
        request_args()
        captured = capsys.readouterr().out.split("\n")
        assert captured[1] == "Invalid date. Will not be included"

    @patch("src.local_invoke.input")
    def test_requests_reference(self, mock_input):
        mock_input.side_effect = ["test", "n", "test_ref"]
        request_args()
        assert mock_input.call_args_list[2].args[0] == "Enter one word reference: "

    @pytest.mark.parametrize(
        "side_effect,expected_print",
        [
            (
                ["test", "n", "test_ref"],
                "Reference: test_ref",
            ),
            (
                ["test", "y", "1997-01-01", "test_ref"],
                "Reference: test_ref",
            ),
            (
                ["test", "y", "1997-01-01", "multiple word reference"],
                "Reference: multiple_word_reference",
            ),
            (
                ["multiple word query", "n", "multiple word reference"],
                "Reference: multiple_word_reference",
            ),
        ],
    )
    @patch("src.local_invoke.input")
    def test_print_reference(self, mock_input, capsys, side_effect, expected_print):
        mock_input.side_effect = side_effect
        request_args()
        captured = capsys.readouterr().out.split("\n")
        assert expected_print in captured

    @patch("src.local_invoke.input")
    def test_returns_dict(self, mock_input):
        mock_input.side_effect = ["test", "n", "test_ref"]
        assert isinstance(request_args(), dict)

    @patch("src.local_invoke.input")
    def test_q_and_ref_keys_and_values_returned(self, mock_input):
        mock_input.side_effect = ["test", "n", "test_ref"]
        output = request_args()
        assert output.get("q") == "test"
        assert output.get("ref") == "test_ref"

    @patch("src.local_invoke.input")
    def test_date_key_not_returned_if_not_given(self, mock_input):
        mock_input.side_effect = ["test", "n", "test_ref"]
        output = request_args()
        assert not output.get("d")

    @patch("src.local_invoke.input")
    def test_d_key_and_value_returned_if_given(self, mock_input):
        mock_input.side_effect = ["test", "y", "1997-01-01", "test_ref"]
        output = request_args()
        assert output.get("d") == "1997-01-01"


class TestSpacesReplaced:
    def test_returns_string(self):
        assert isinstance(_spaces_replaced(""), str)

    def test_output_contains_no_spaces(self):
        assert " " not in _spaces_replaced("one two three")

    def test_spaces_replaced_with_underscores(self):
        assert _spaces_replaced("a b c d e") == "a_b_c_d_e"


class TestInvokeLambda:
    def test_returns_response_dict(self, aws_credentials, args):
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.return_value = {"statusCode": 200}
        output = invoke_lambda(mock_lambda_client, "test", args)
        assert isinstance(output, dict)
        assert output == {"statusCode": 200}

    # create mock lambda function? or just mock response
    # assert lambda called?
    # use moto to check lambda call is properly formed?
    def test_lambda_invoked(self, aws_credentials, args):
        mock_lambda_client = Mock()
        invoke_lambda(mock_lambda_client, "test", args)
        assert mock_lambda_client.invoke.call_args.kwargs.get("FunctionName") == "test"
        assert list(mock_lambda_client.invoke.call_args.kwargs.keys()) == [
            "FunctionName",
            "InvocationType",
            "LogType",
            "ClientContext",
            "Payload",
            "Qualifier",
        ]

class TestLambdaName:
    @patch('src.local_invoke.load_dotenv')
    def test_loads_name_from_env(self, mock_load, monkeypatch):
        monkeypatch.setenv('LAMBDA_NAME', 'test_name')
        assert _lambda_name() == 'test_name'
        assert mock_load.call_count == 1

    @patch('src.local_invoke.load_dotenv')
    def test_raises_error_if_not_found(self, mock_load):
        with pytest.raises(EnvironmentError) as e:
            _lambda_name()
        assert str(e.value) == "LAMBDA_NAME retrieval from .env unsuccessful"
    

# class TestMain:
#     def test_dummy(self):
#         main()


@pytest.fixture(scope="function")
def args():
    return {"q": "test", "d": "1997-01-01", "ref": "ref"}


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


# @pytest.fixture(scope="function")
# def aws_lambda(aws_credentials):
#     """
#     Return a mocked Lambda client
#     """
#     with mock_aws():
#         iam_client = boto3.client('iam')
#         role_name = 'test_lambda_role'
#         policy = iam_client.create_policy(
#         PolicyName='AWSLambdaBasicExecutionRole',
#         PolicyDocument='''{
#             "Version": "2012-10-17",
#             "Statement": [
#                 {
#                     "Effect": "Allow",
#                     "Action": "logs:CreateLogGroup",
#                     "Resource": "*"
#                 }
#             ]
#         }'''
#         )
#         assume_role_policy = {
#             "Version": "2012-10-17",
#             "Statement": [
#                 {
#                 "Effect": "Allow",
#                 "Principal": {
#                     "Service": "lambda.amazonaws.com"
#                 },
#                 "Action": "sts:AssumeRole"
#                 }
#                 ]
#             }
#         response = iam_client.create_role(
#             RoleName=role_name,
#             AssumeRolePolicyDocument=json.dumps(assume_role_policy),
#             Description='IAM role for Lambda function execution'
#             )
#         role_arn = response['Role']['Arn']

#         iam_client.attach_role_policy(
#             RoleName=role_name,
#             PolicyArn=policy['Policy']['Arn']
#             )


#         client = boto3.client("lambda")
#         client.create_function(
#             FunctionName="test_lambda",
#             Runtime="python3.8",
#             Role=role_arn,
#             Handler="lambda_function.lambda_handler",
#             Code={"ZipFile": create_lambda_zip()},
#             Description="Test Lambda function",
#             Timeout=3,
#             MemorySize=128,
#             Publish=True,
#             )
#         yield client

# def create_lambda_zip():
#     code = '''
# def lambda_handler(event, context):
#     print(event)
#     return {"statusCode": 200, "body": "Hello from Lambda"}
# '''
#     zip_buffer = io.BytesIO()
#     with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
#         zip_file.writestr("lambda_function.py", code)
#     zip_buffer.seek(0)
#     return zip_buffer.read()
