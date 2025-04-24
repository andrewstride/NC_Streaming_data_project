from src.lambda_function import lambda_handler, _env_variables, _build_url, _parse_results, BASE_URL
from unittest.mock import patch
import pytest
import re
import requests
import logging
import json


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
    def test_logs_error_for_missing_q_or_ref_keys(self, mock_requests, caplog):
        with caplog.at_level(logging.ERROR):
            lambda_handler({"ref": "test"}, {})
            assert any("Missing required event key: q" in m for m in caplog.messages)

            caplog.clear()

            lambda_handler({"q": "test"}, {})
            assert any("Missing required event key: ref" in m for m in caplog.messages)

    @patch("src.lambda_function.requests")
    def test_logs_event_at_info_level(self, mock_requests, caplog):
        with caplog.at_level(logging.INFO):
            lambda_handler({}, {})
            assert any("Invoked with event: {}" in m for m in caplog.messages)

            caplog.clear()

            lambda_handler({"q": "test", "ref": "test"}, {})
            assert any(
                "Invoked with event: {" in m
                and "'q': 'test'" in m
                and "'ref': 'test'" in m
                for m in caplog.messages
            )

            caplog.clear()

            lambda_handler({"q": "test", "d": "2001-05-06", "ref": "test"}, {})
            assert any(
                "Invoked with event: {" in m
                and "'q': 'test'" in m
                and "'ref': 'test'}" in m
                and "'d': '2001-05-06'" in m
                for m in caplog.messages
            )

class TestParseResults:
    def test_returns_list(self, api_200_response):
        results = api_200_response['response']['results']
        assert isinstance(_parse_results(results), list)

    def test_returns_mvp_keys(self, api_200_response):
        results = api_200_response['response']['results']
        output = _parse_results(results)
        expected_keys = ["webTitle", "webUrl", "webPublicationDate"]
        assert len(output) > 0
        for result in output:
            for key in expected_keys:
                assert key in list(result.keys())

    def test_unwanted_keys_not_returned(self, api_200_response):
        results = api_200_response['response']['results']
        output = _parse_results(results)
        unwanted_keys = ['id', 'type', 'sectionId', 'sectionName', 'apiUrl', 'isHosted', 'pillarId', 'pillarName']
        assert len(output) > 0
        for result in output:
            for key in unwanted_keys:
                assert key not in list(result.keys())
            



@pytest.fixture(scope="function")
def event_no_date():
    return {"q": "test%20query", "ref": "test_ref"}


@pytest.fixture(scope="function")
def event_with_date():
    return {"q": "test%20query", "d": "1997-01-01", "ref": "test_ref"}

@pytest.fixture(scope="function")
def api_200_response():
    return json.loads("""{
	"response": {
		"status": "ok",
		"userTier": "developer",
		"total": 178192,
		"startIndex": 1,
		"pageSize": 10,
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
			},
			{
				"id": "society/2025/apr/12/blood-test-could-detect-parkinsons-disease-before-symptoms-emerge",
				"type": "article",
				"sectionId": "society",
				"sectionName": "Society",
				"webPublicationDate": "2025-04-12T16:33:57Z",
				"webTitle": "Blood test could detect Parkinson’s disease before symptoms emerge",
				"webUrl": "https://www.theguardian.com/society/2025/apr/12/blood-test-could-detect-parkinsons-disease-before-symptoms-emerge",
				"apiUrl": "https://content.guardianapis.com/society/2025/apr/12/blood-test-could-detect-parkinsons-disease-before-symptoms-emerge",
				"isHosted": false,
				"pillarId": "pillar/news",
				"pillarName": "News"
			},
			{
				"id": "society/2024/dec/17/prisons-crisis-will-test-labours-mettle",
				"type": "article",
				"sectionId": "society",
				"sectionName": "Society",
				"webPublicationDate": "2024-12-17T17:27:21Z",
				"webTitle": "Prisons crisis will test Labour’s mettle | Letters",
				"webUrl": "https://www.theguardian.com/society/2024/dec/17/prisons-crisis-will-test-labours-mettle",
				"apiUrl": "https://content.guardianapis.com/society/2024/dec/17/prisons-crisis-will-test-labours-mettle",
				"isHosted": false,
				"pillarId": "pillar/news",
				"pillarName": "News"
			},
			{
				"id": "business/2025/mar/21/borrowing-overshoot-will-test-rachel-reeves-resolve-on-tax-rises",
				"type": "article",
				"sectionId": "business",
				"sectionName": "Business",
				"webPublicationDate": "2025-03-21T09:20:28Z",
				"webTitle": "Borrowing overshoot will test Rachel Reeves’s resolve on tax rises",
				"webUrl": "https://www.theguardian.com/business/2025/mar/21/borrowing-overshoot-will-test-rachel-reeves-resolve-on-tax-rises",
				"apiUrl": "https://content.guardianapis.com/business/2025/mar/21/borrowing-overshoot-will-test-rachel-reeves-resolve-on-tax-rises",
				"isHosted": false,
				"pillarId": "pillar/news",
				"pillarName": "News"
			},
			{
				"id": "sport/2025/mar/09/devastated-england-wait-for-test-results-after-ollie-lawrence-injury",
				"type": "article",
				"sectionId": "sport",
				"sectionName": "Sport",
				"webPublicationDate": "2025-03-09T19:44:06Z",
				"webTitle": "‘Devastated’ England wait for test results after Ollie Lawrence injury",
				"webUrl": "https://www.theguardian.com/sport/2025/mar/09/devastated-england-wait-for-test-results-after-ollie-lawrence-injury",
				"apiUrl": "https://content.guardianapis.com/sport/2025/mar/09/devastated-england-wait-for-test-results-after-ollie-lawrence-injury",
				"isHosted": false,
				"pillarId": "pillar/sport",
				"pillarName": "Sport"
			},
			{
				"id": "sport/2025/mar/12/rugby-union-six-nations-england-wales-steve-borthwick-selection",
				"type": "article",
				"sectionId": "sport",
				"sectionName": "Sport",
				"webPublicationDate": "2025-03-12T20:23:44Z",
				"webTitle": "Borthwick deserves credit after bold selection for England’s Wales test",
				"webUrl": "https://www.theguardian.com/sport/2025/mar/12/rugby-union-six-nations-england-wales-steve-borthwick-selection",
				"apiUrl": "https://content.guardianapis.com/sport/2025/mar/12/rugby-union-six-nations-england-wales-steve-borthwick-selection",
				"isHosted": false,
				"pillarId": "pillar/sport",
				"pillarName": "Sport"
			},
			{
				"id": "society/2025/mar/31/new-blood-test-checks-alzheimers-assesses-progression",
				"type": "article",
				"sectionId": "society",
				"sectionName": "Society",
				"webPublicationDate": "2025-03-31T15:00:51Z",
				"webTitle": "New blood test checks for Alzheimer’s and assesses progression, study says",
				"webUrl": "https://www.theguardian.com/society/2025/mar/31/new-blood-test-checks-alzheimers-assesses-progression",
				"apiUrl": "https://content.guardianapis.com/society/2025/mar/31/new-blood-test-checks-alzheimers-assesses-progression",
				"isHosted": false,
				"pillarId": "pillar/news",
				"pillarName": "News"
			},
			{
				"id": "football/2025/mar/30/english-football-mascots-quiz",
				"type": "article",
				"sectionId": "football",
				"sectionName": "Football",
				"webPublicationDate": "2025-03-30T10:00:17Z",
				"webTitle": "Quiz: test your knowledge of English football’s weird and wonderful mascots",
				"webUrl": "https://www.theguardian.com/football/2025/mar/30/english-football-mascots-quiz",
				"apiUrl": "https://content.guardianapis.com/football/2025/mar/30/english-football-mascots-quiz",
				"isHosted": false,
				"pillarId": "pillar/sport",
				"pillarName": "Sport"
			},
			{
				"id": "sport/2025/apr/21/cricket-wisden-world-test-championship-india-south-africa-graham-thorpe",
				"type": "article",
				"sectionId": "sport",
				"sectionName": "Sport",
				"webPublicationDate": "2025-04-21T21:30:47Z",
				"webTitle": "Wisden calls World Test Championship a ‘shambles’ and makes case for reform",
				"webUrl": "https://www.theguardian.com/sport/2025/apr/21/cricket-wisden-world-test-championship-india-south-africa-graham-thorpe",
				"apiUrl": "https://content.guardianapis.com/sport/2025/apr/21/cricket-wisden-world-test-championship-india-south-africa-graham-thorpe",
				"isHosted": false,
				"pillarId": "pillar/sport",
				"pillarName": "Sport"
			},
			{
				"id": "sport/2025/mar/14/rory-mcilroy-relishing-tougher-test-as-storms-head-for-players-championship",
				"type": "article",
				"sectionId": "sport",
				"sectionName": "Sport",
				"webPublicationDate": "2025-03-14T18:59:51Z",
				"webTitle": "Rory McIlroy relishing tougher test as storms head for Players Championship",
				"webUrl": "https://www.theguardian.com/sport/2025/mar/14/rory-mcilroy-relishing-tougher-test-as-storms-head-for-players-championship",
				"apiUrl": "https://content.guardianapis.com/sport/2025/mar/14/rory-mcilroy-relishing-tougher-test-as-storms-head-for-players-championship",
				"isHosted": false,
				"pillarId": "pillar/sport",
				"pillarName": "Sport"
			}
		]
	}
}""")
