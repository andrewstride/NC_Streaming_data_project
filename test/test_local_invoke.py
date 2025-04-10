from src.local_invoke import main, parse_args
import shlex

class TestParseArgs:
    def test_returns_dict(self):
        assert isinstance(parse_args(['q','r']), dict)
