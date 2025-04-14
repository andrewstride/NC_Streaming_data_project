from src.local_invoke import main, parse_args
import shlex
import pytest


class TestParseArgs:
    def test_returns_dict(self):
        assert isinstance(parse_args(shlex.split("-q q -ref ref")), dict)

    def test_returns_none_if_no_args(self):
        assert parse_args() == None

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
        assert parse_args(test_input) == None
