from src.lambda_function import lambda_handler, _env_variables, _build_url, BASE_URL
from unittest.mock import patch
import pytest
import re
import requests


class TestEnvVariablesUtil:
    @patch('src.lambda_function.os')
    def test_accesses_os_get(self, mock_os):
        mock_os.environ.get.side_effect = ['env_1', 'env_2']
        _env_variables()
        assert mock_os.environ.get.call_count == 2

    @patch('src.lambda_function.os')
    def test_uses_correct_env_key_names(self, mock_os):
        mock_os.environ.get.side_effect = ['env_1', 'env_2']
        _env_variables()
        call_list = mock_os.environ.get.call_args_list 
        call_list = [call[0][0] for call in call_list]
        assert call_list == [
            "api_key",
            "sqs_queue_url"
        ]

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
        args = ['test_query', "test_api_key"]
        kwargs= {"date": '1997-01-01'}
        assert isinstance(_build_url(*args, **kwargs), str)

    def test_url_format_correct_with_date(self):
        url = _build_url("test", "test", '1997-01-01')
        pattern = r"https:\/\/content.guardianapis.com\/search\?q=[a-z]+&from-date=[\d]{4}-[\d]{2}-[\d]{2}&api-key=test"
        assert re.match(pattern, url)

    def test_url_format_correct_without_date(self):
        url = _build_url("test", "test")
        pattern = r"https:\/\/content.guardianapis.com\/search\?q=[a-z]+&api-key=test"
        assert re.match(pattern, url)


class TestHandler:
    @patch('src.lambda_function.requests')
    def test_returns_400_for_malformed_event(self, mock_requests):
        output = lambda_handler({}, {})
        expected = {
            "statusCode": 400,
            "error": "Bad request",
            "message": "Missing required event key: q - 'q' and 'ref' required"
        }
        assert output == expected

@pytest.fixture(scope="function")
def event_no_date():
    return {
        'q': 'test%20query',
        'ref': 'test_ref'
    }

@pytest.fixture(scope="function")
def event_with_date():
    return {
        'q': 'test%20query',
        'd': '1997-01-01',
        'ref': 'test_ref'
    }
