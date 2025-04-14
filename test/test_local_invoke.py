from src.local_invoke import main, parse_args, _is_valid_date
import shlex
import pytest


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


class TestMain:
    def test_dummy(self):
        main()
