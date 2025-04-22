from src.lambda_function import lambda_handler, _env_variables, _build_url
from unittest.mock import patch
import pytest


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
        output = _env_variables()
        assert output.get("api_key") == "test_key"
        assert output.get("sqs_queue_url") == "test_url"

class TestBuildUrl:
    def test_returns_string(self):
        args = ['test_query', "test_ref", "test_api_key"]
        kwargs= {"date": '1997-01-01'}
        assert isinstance(_build_url(*args, **kwargs), str)

class TestHandler:
    def test_accesses_env_variables(self):
        # set env variables for Guardian API key & SQS Queue name
        # mock os.environ.get.called_with
        lambda_handler({}, {})

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
