from src.lambda_function import (
    lambda_handler,
    _env_variables,
    _build_url,
    _parse_results,
    _fetch_data,
    _get_sqs_client,
    _send_to_SQS,
    BASE_URL,
)
from unittest.mock import patch, Mock
from botocore.exceptions import ClientError
from moto import mock_aws
import pytest
import re
import requests
import logging
import json
import boto3
import os


class TestHandler:
    @patch("src.lambda_function.requests")
    def test_returns_400_for_malformed_event(self, mock_requests):
        output = lambda_handler({}, {})
        expected = {
            "statusCode": 400,
            "error": "Bad request",
            "message": "Missing required event key: q - 'q' and 'ref' required",
        }
        assert output == expected

    @patch("src.lambda_function.requests")
    def test_logs_error_for_missing_q_or_ref_event_keys_and_returns_error(
        self, mock_requests, caplog
    ):
        with caplog.at_level(logging.ERROR):
            response = lambda_handler({"ref": "test"}, {})
            assert any("Missing required event key: q" in m for m in caplog.messages)
            assert response == {
                "statusCode": 400,
                "error": "Bad request",
                "message": "Missing required event key: q - 'q' and 'ref' required",
            }
            caplog.clear()

            response = lambda_handler({"q": "test"}, {})
            assert any("Missing required event key: ref" in m for m in caplog.messages)
            assert response == {
                "statusCode": 400,
                "error": "Bad request",
                "message": "Missing required event key: ref - 'q' and 'ref' required",
            }

    @patch("src.lambda_function.requests")
    def test_logs_event_at_info_level(
        self, mock_requests, caplog, event_no_date, event_with_date
    ):
        with caplog.at_level(logging.INFO):
            lambda_handler({}, {})
            assert any("Invoked with event: {}" in m for m in caplog.messages)

            caplog.clear()

            lambda_handler(event_no_date, {})
            assert any(
                "Invoked with event: {" in m
                and "'q': 'test%20query'" in m
                and "'ref': 'test_ref'" in m
                for m in caplog.messages
            )

            caplog.clear()

            lambda_handler(event_with_date, {})
            assert any(
                "Invoked with event: {" in m
                and "'q': 'test%20query'" in m
                and "'ref': 'test_ref'}" in m
                and "'d': '1997-01-01'" in m
                for m in caplog.messages
            )

    @patch("src.lambda_function.requests.get")
    def test_logs_progress_and_returns_dict_with_message_log(
        self,
        mock_requests,
        event_with_date,
        monkeypatch,
        api_200_response,
        mock_sqs_moto_and_url_in_env,
        caplog,
    ):
        mock_requests.return_value = api_200_response
        monkeypatch.setenv("api_key", "test_key")
        assert (
            os.environ.get("sqs_queue_url")
            == "https://sqs.eu-west-2.amazonaws.com/123456789012/test_queue.fifo"
        )
        assert os.environ.get("AWS_ACCESS_KEY_ID") == "FOOBARKEY"
        with caplog.at_level(logging.INFO):
            response = lambda_handler(event_with_date, {})
            assert any(
                "Attempting to retrieve environment variables" in m
                or "Environment variables retrieved" in m
                or "URL built, attempting API call" in m
                or "1 result(s) collected" in m
                or "Message sent. ID:" in m
                for m in caplog.messages
            )
        assert response == {
            "statusCode": 200,
            "messagesSent": 1,
            "messagesFailed": 0,
            "messages": [
                {
                    "webTitle": "At-home saliva test for prostate cancer better than blood test, study suggests",
                    "webUrl": "https://www.theguardian.com/society/2025/apr/09/at-home-saliva-test-for-prostate-cancer-better-than-blood-test-study-suggests",
                    "webPublicationDate": "2025-04-09T21:00:09Z",
                    "reference": "test_ref",
                }
            ],
        }

    @patch("src.lambda_function._send_to_SQS")
    @patch("src.lambda_function.requests.get")
    def test_returns_dict_with_failed_message_log(
        self,
        mock_requests,
        mock_send_to_SQS,
        event_with_date,
        monkeypatch,
        api_200_response,
        mock_sqs_moto_and_url_in_env,
    ):
        mock_requests.return_value = api_200_response
        monkeypatch.setenv("api_key", "test_key")
        assert (
            os.environ.get("sqs_queue_url")
            == "https://sqs.eu-west-2.amazonaws.com/123456789012/test_queue.fifo"
        )
        assert os.environ.get("AWS_ACCESS_KEY_ID") == "FOOBARKEY"
        mock_send_to_SQS.return_value = False
        response = lambda_handler(event_with_date, {})
        assert response["messagesFailed"] == 1


class TestEnvVariablesUtil:
    @patch("src.lambda_function.os")
    def test_accesses_os_get(self, mock_os):
        mock_os.environ.get.side_effect = ["env_1", "env_2"]
        _env_variables()
        assert mock_os.environ.get.call_count == 2

    @patch("src.lambda_function.os")
    def test_uses_correct_env_key_names(self, mock_os):
        mock_os.environ.get.side_effect = ["env_1", "env_2"]
        _env_variables()
        call_list = mock_os.environ.get.call_args_list
        call_list = [call[0][0] for call in call_list]
        assert call_list == ["api_key", "sqs_queue_url"]

    def test_collects_values(self, monkeypatch):
        monkeypatch.setenv("api_key", "test_key")
        monkeypatch.setenv("sqs_queue_url", "test_url")
        api_key, sqs_queue_url = _env_variables()
        assert api_key == "test_key"
        assert sqs_queue_url == "test_url"

    def test_raises_exception_if_sqs_var_not_found(self, monkeypatch):
        monkeypatch.setenv("api_key", "test_key")
        with pytest.raises(KeyError) as e:
            _env_variables()
        assert "Missing environment variable: sqs_queue_url" in str(e.value)

    def test_raises_exception_if_api_key_var_not_found(self, monkeypatch):
        monkeypatch.setenv("sqs_queue_url", "test_url")
        with pytest.raises(KeyError) as e:
            _env_variables()
        assert "Missing environment variable: api_key" in str(e.value)


class TestBASEURL:
    def test_returns_200(self):
        response = requests.get(BASE_URL + "&api-key=test")
        assert response.status_code == 200


class TestBuildUrl:
    def test_returns_string(self):
        args = ["test_query", "test_api_key"]
        kwargs = {"date": "1997-01-01"}
        assert isinstance(_build_url(*args, **kwargs), str)

    def test_url_format_correct_with_date(self):
        url = _build_url("test", "test", "1997-01-01")
        pattern = r"https:\/\/content.guardianapis.com\/search\?q=[a-z]+&from-date=[\d]{4}-[\d]{2}-[\d]{2}&api-key=test"
        assert re.match(pattern, url)

    def test_url_format_correct_without_date(self):
        url = _build_url("test", "test")
        pattern = r"https:\/\/content.guardianapis.com\/search\?q=[a-z]+&api-key=test"
        assert re.match(pattern, url)


class TestParseResults:
    def test_returns_list(self, response_body):
        results = response_body["response"]["results"]
        assert isinstance(_parse_results(results, "test_ref"), list)

    def test_returns_mvp_keys_and_reference(self, response_body):
        results = response_body["response"]["results"]
        output = _parse_results(results, "test_ref")
        expected_keys = ["webTitle", "webUrl", "webPublicationDate", "reference"]
        assert len(output) > 0
        for result in output:
            for key in expected_keys:
                assert key in list(result.keys())

    def test_unwanted_keys_not_returned(self, response_body):
        results = response_body["response"]["results"]
        output = _parse_results(results, "test_ref")
        unwanted_keys = [
            "id",
            "type",
            "sectionId",
            "sectionName",
            "apiUrl",
            "isHosted",
            "pillarId",
            "pillarName",
        ]
        assert len(output) > 0
        for result in output:
            for key in unwanted_keys:
                assert key not in list(result.keys())


class TestFetchData:
    @patch("src.lambda_function.requests")
    def test_api_called_with_url(self, mock_requests):
        _fetch_data("test_url")
        called_with = mock_requests.get.call_args_list[0][0][0]
        assert called_with == "test_url"

    @patch("src.lambda_function.requests")
    def test_returns_list(self, mock_requests, api_200_response):
        mock_requests.get.return_value = api_200_response
        assert isinstance(_fetch_data("test_url"), list)

    @patch("src.lambda_function.requests")
    def test_logs_results(self, mock_requests, api_200_response, caplog):
        mock_requests.get.return_value = api_200_response
        with caplog.at_level(logging.INFO):
            _fetch_data("test_url")
            assert any("1 result(s) collected" in m for m in caplog.messages)

    @patch("src.lambda_function.requests.get")
    def test_handles_malformed_response(
        self, mock_requests, caplog, api_200_malformed_payload
    ):
        mock_requests.return_value = api_200_malformed_payload
        with caplog.at_level(logging.ERROR):
            with pytest.raises(KeyError):
                _fetch_data("test_url")
            assert any(
                "Error while fetching data:" in m
                and "KeyError" in m
                and "response" in m
                for m in caplog.messages
            )

    @patch("src.lambda_function.requests.get")
    def test_logs_error(self, mock_requests, caplog, api_401_response):
        mock_requests.return_value = api_401_response
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.HTTPError):
                _fetch_data("test_url")
            assert any(
                "HTTP Error while fetching data:" in m and "401 Unauthorized" in m
                for m in caplog.messages
            )

    @patch("src.lambda_function.requests.get")
    def test_handles_timeout(self, mock_requests, caplog):
        mock_requests.side_effect = requests.exceptions.Timeout("Request timed out")
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.Timeout):
                _fetch_data("test_url")
            assert any(
                "Timeout occurred while fetching data:" in m
                and "Request timed out" in m
                for m in caplog.messages
            )


class TestGetSqsClient:
    @mock_aws
    def test_returns_boto3_client(self):
        client = _get_sqs_client()
        assert client.__class__.__name__ == "SQS"


class TestSendToSQS:
    def test_calls_client_with_send_message_url_and_message(
        self, mock_sqs_client, message
    ):
        _send_to_SQS(message, "test_ref", mock_sqs_client, "test_url")
        mock_sqs_client.send_message.assert_called_with(
            QueueUrl="test_url",
            MessageBody=json.dumps(message),
            MessageGroupId="test_ref",
        )

    def test_logs_message_sent_and_returns_true(self, caplog, mock_sqs_client, message):
        with caplog.at_level(logging.INFO):
            output = _send_to_SQS(message, "test_ref", mock_sqs_client, "test_url")

            assert any("Message sent. ID: test_id" in m for m in caplog.messages)
        assert output

    def test_logs_client_error_and_returns_false(self, caplog, message):
        sqs_client_error = Mock()
        error_response = {"Error": {"Code": "AccessDenied", "Message": "test_message"}}
        sqs_client_error.send_message.side_effect = ClientError(
            error_response, "SendMessage"
        )

        with caplog.at_level(logging.ERROR):
            output = _send_to_SQS(message, "test_ref", sqs_client_error, "test_url")
            assert any(
                "Failed to send message: test_message" in m for m in caplog.messages
            )
        assert not output

    def test_handles_unexpected_error(self, caplog, message):
        sqs_client_error = Mock()
        sqs_client_error.send_message.return_value = "unexpected_value"
        with caplog.at_level(logging.ERROR):
            output = _send_to_SQS(message, "test_ref", sqs_client_error, "test_url")
            assert any(
                "Unexpected error when sending message" in m for m in caplog.messages
            )
        assert not output

    def test_message_sent_to_queue(self, message, mock_sqs_moto_and_url_in_env):
        sqs_url = os.environ.get("sqs_queue_url")
        assert os.environ.get("AWS_ACCESS_KEY_ID") == "FOOBARKEY"
        sqs_client = mock_sqs_moto_and_url_in_env
        output = _send_to_SQS(message, "test_ref", sqs_client, sqs_url)
        assert output
        response = sqs_client.receive_message(QueueUrl=sqs_url)
        assert response["Messages"][0]["Body"] == json.dumps(message)


@pytest.fixture(scope="function")
def event_no_date():
    return {"q": "test%20query", "ref": "test_ref"}


@pytest.fixture(scope="function")
def event_with_date():
    return {"q": "test%20query", "d": "1997-01-01", "ref": "test_ref"}


@pytest.fixture(scope="function")
def api_200_response(response_body):
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.ok = True
    response.json.return_value = response_body
    return response


@pytest.fixture(scope="function")
def response_body():
    return json.loads("""{
	"response": {
		"status": "ok",
		"userTier": "developer",
		"total": 178192,
		"startIndex": 1,
		"pageSize": 1,
		"currentPage": 1,
		"pages": 17820,
		"orderBy": "relevance",
		"results": [
			{
				"id": "society/2025/apr/09/at-home-saliva-test-for-prostate-cancer-better-than-blood-test-study-suggests",
				"type": "article",
				"sectionId": "society",
				"sectionName": "Society",
				"webPublicationDate": "2025-04-09T21:00:09Z",
				"webTitle": "At-home saliva test for prostate cancer better than blood test, study suggests",
				"webUrl": "https://www.theguardian.com/society/2025/apr/09/at-home-saliva-test-for-prostate-cancer-better-than-blood-test-study-suggests",
				"apiUrl": "https://content.guardianapis.com/society/2025/apr/09/at-home-saliva-test-for-prostate-cancer-better-than-blood-test-study-suggests",
				"isHosted": false,
				"pillarId": "pillar/news",
				"pillarName": "News"
			}
		]
	}
}""")


@pytest.fixture(scope="function")
def api_401_response():
    response = Mock(spec=requests.Response)
    response.status_code = 401
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "401 Unauthorized"
    )
    response.ok = False
    response.json.return_value = {"message": "Unauthorized"}
    return response


@pytest.fixture(scope="function")
def api_200_malformed_payload():
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.ok = True
    response.json.return_value = {"message": "test"}
    return response


@pytest.fixture(scope="function")
def mock_sqs_client():
    response = {
        "MD5OfMessageBody": "string",
        "MD5OfMessageAttributes": "string",
        "MD5OfMessageSystemAttributes": "string",
        "MessageId": "test_id",
        "SequenceNumber": "string",
    }
    sqs_client = Mock()
    sqs_client.send_message.return_value = response
    return sqs_client


@pytest.fixture(scope="function")
def message():
    return {"WebURL": "test", "reference": "test_ref"}


@pytest.fixture(scope="function")
def mock_sqs_moto_and_url_in_env(monkeypatch):
    with mock_aws():
        print(os.environ.get("AWS_REGION"))
        conn = boto3.client("sqs")
        response = conn.create_queue(
            QueueName="test_queue.fifo",
            Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
        )
        monkeypatch.setenv("sqs_queue_url", response["QueueUrl"])
        yield conn
