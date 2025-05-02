from src.local_invoke import (
    parse_args,
    is_valid_date,
    request_args,
    spaces_replaced,
    invoke_lambda,
    lambda_name,
    get_args,
    handle_lambda_response,
)
from unittest.mock import patch, Mock
from botocore.response import StreamingBody
from botocore.exceptions import ClientError
import shlex
import pytest
import os
import json
import base64
import io


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
        assert isinstance(is_valid_date(""), bool)
        assert isinstance(is_valid_date("2013-01-02"), bool)
        assert isinstance(is_valid_date("test"), bool)

    def test_returns_true_for_YYYY_MM_DD_date(self):
        assert is_valid_date("2001-01-05")
        assert is_valid_date("1997-12-21")
        assert is_valid_date("1982-06-28")

    def test_returns_false_for_not_YYYY_MM_DD_string(self):
        assert not is_valid_date("123-12-12")
        assert not is_valid_date("test")
        assert not is_valid_date("2001-23")
        assert not is_valid_date("1001-10-10-1")

    def test_returns_false_for_month_or_date_out_of_range(self):
        assert not is_valid_date("2001-13-01")
        assert not is_valid_date("1997-01-32")

    def test_handles_incorrect_input_format(self):
        assert not is_valid_date(234)
        assert not is_valid_date(True)
        assert not is_valid_date({"test": "dict"})


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
        assert isinstance(spaces_replaced(""), str)

    def test_output_contains_no_spaces(self):
        assert " " not in spaces_replaced("one two three")

    def test_spaces_replaced_with_underscores(self):
        assert spaces_replaced("a b c d e") == "a_b_c_d_e"


class TestInvokeLambda:
    def test_returns_response_dict(self, aws_credentials, args):
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.return_value = {"statusCode": 200}
        output = invoke_lambda(mock_lambda_client, "test", args)
        assert isinstance(output, dict)
        assert output == {"statusCode": 200}

    def test_lambda_invoked(self, aws_credentials, args):
        mock_lambda_client = Mock()
        invoke_lambda(mock_lambda_client, "test", args)
        assert mock_lambda_client.invoke.call_args.kwargs.get("FunctionName") == "test"
        assert list(mock_lambda_client.invoke.call_args.kwargs.keys()) == [
            "FunctionName",
            "InvocationType",
            "LogType",
            "Payload",
        ]

    def test_handles_boto3_error(self, args):
        error_response = {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "You are not authorized to perform this operation.",
            }
        }
        mock_lambda_raises_exc = Mock()
        mock_lambda_raises_exc.invoke.side_effect = ClientError(
            error_response, "Invoke"
        )
        with pytest.raises(RuntimeError, match="Failed to invoke Lambda"):
            invoke_lambda(mock_lambda_raises_exc, "test", args)


class TestLambdaName:
    @patch("src.local_invoke.load_dotenv")
    def test_loads_name_from_env(self, mock_load, monkeypatch):
        monkeypatch.setenv("LAMBDA_NAME", "test_name")
        assert lambda_name() == "test_name"
        assert mock_load.call_count == 1

    @patch("src.local_invoke.load_dotenv")
    def test_raises_error_if_not_found(self, mock_load):
        with pytest.raises(EnvironmentError) as e:
            lambda_name()
        assert str(e.value) == "LAMBDA_NAME retrieval from .env unsuccessful"


class TestGetArgs:
    @patch("src.local_invoke.parse_args")
    def test_invokes_parse_args_and_returns_result(self, mock_parse_args):
        mock_parse_args.return_value = "expected result"
        assert get_args() == "expected result"
        mock_parse_args.assert_called_once()

    @patch("src.local_invoke.parse_args")
    @patch("src.local_invoke.request_args")
    def test_invokes_request_args_if_parse_args_returns_none(
        self, mock_request_args, mock_parse_args
    ):
        mock_parse_args.return_value = None
        mock_request_args.return_value = "expected result"
        assert get_args() == "expected result"
        mock_request_args.assert_called_once()


class TestHandleLambdaResponse:
    def test_prints_payload_if_successful(self, lambda_200_response, capsys):
        handle_lambda_response(lambda_200_response)
        captured = capsys.readouterr().out.split("\n")
        assert captured[0] == "Successful response"
        assert captured[1] == "10 message(s) sent"
        assert captured[2] == "0 message(s) failed"
        assert captured[3] == "Messages sent:"
        assert captured[4] == str({"example": "message1"})
        assert captured[5] == str({"example": "message2"})

    def test_prints_error_details_if_present(self, lambda_response_with_error, capsys):
        handle_lambda_response(lambda_response_with_error)
        captured = capsys.readouterr().out.split("\n")
        assert (
            "Error handling payload: 'str' object has no attribute 'read'"
            in captured[0]
        )
        assert captured[1] == "Unhandled Lambda Function Error"

    def test_handles_malformed_response(self, capsys):
        handle_lambda_response({})
        captured = capsys.readouterr().out.split("\n")
        assert captured[0] == "Invalid Lambda response"

    def test_handles_non_2xx_response(self, capsys):
        handle_lambda_response({"StatusCode": 500, "FunctionError": "Handled"})
        captured = capsys.readouterr().out.split("\n")
        assert captured[0] == "Invalid Lambda response"
        assert captured[1] == "Status Code: 500"
        assert captured[2] == "Handled Lambda Function Error"


# class TestMain:
#     def test_invokes_args_functions(self):
#         main()


@pytest.fixture(scope="function")
def lambda_response_with_error():
    return {
        "StatusCode": 200,
        "FunctionError": "Unhandled",
        "Payload": '{"errorMessage": "TypeError: unsupported operand type(s) for +: \'int\' and \'str\'", "errorType": "TypeError", "stackTrace": ["File "/var/task/index.py", line 23, in lambda_handler"]}',
        "LogResult": "YmFzZTY0ZWVuY29kZWQgbG9nIGluIGxhbWJkYSBmZWF0dXJlcyBvciBzb21lIGV4Y2VwdGlvbnMgb3ZlciBsb2cu",
        "ExecutedVersion": "$LATEST",
        "ResponseMetadata": {
            "RequestId": "12345678-90ab-cdef-ghij-klmnopqrst",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "12345678-90ab-cdef-ghij-klmnopqrst",
                "x-amz-function-error": "Unhandled",
                "x-amz-id-2": "s23yWl0Wh2teo5ihGVpHlpcOB5TZk8Tx5DgGc3tT00V5t2vF1O5Vp25Ad5wz8NnEB6d8BzIu7TI=",
            },
        },
    }


@pytest.fixture(scope="function")
def lambda_200_response():
    payload = {
        "statusCode": 200,
        "messagesSent": 10,
        "messagesFailed": 0,
        "messages": [{"example": "message1"}, {"example": "message2"}],
    }

    payload_bytes = json.dumps(payload).encode("utf-8")
    streaming_body = StreamingBody(io.BytesIO(payload_bytes), len(payload_bytes))

    log_output = "10 Messages Sent"
    log_output_base64 = base64.b64encode(log_output.encode("utf-8")).decode("utf-8")

    return {
        "ResponseMetadata": {"meta": "data"},
        "StatusCode": 200,
        "LogResult": log_output_base64,
        "ExecutedVersion": "$LATEST",
        "Payload": streaming_body,
    }


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
