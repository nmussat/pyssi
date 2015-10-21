import requests

from pyssi import Parser
from unittest.mock import MagicMock


TESTS = [
    ('<div>Noop</div>', {}, '<div>Noop</div>'),
    ('<!--# block name="name" -->foo<!--# endblock --><!--# echo var="name" -->', {}, 'foo'),
    ('<!--# echo var="foo" -->', {}, '[an error occurred while processing the directive]'),
    ('<!--# config errmsg="error message" --><!--# echo var="foo" -->', {}, 'error message'),
    ('<!--# config timefmt="timefmt" --><!--# echo var="timefmt" -->', {}, 'timefmt'),
    ('<!--# echo var="name" -->', {'name': 'foo'}, 'foo'),
    ('<!--# echo var="name" default="bar"-->', {}, 'bar'),
    ('<!--# if expr="$name" -->foo<!--# endif -->', {'name': 'foo'}, 'foo'),
    ('<!--# if expr="$name" -->foo<!--# else -->bar<!--# endif -->', {'name': 'foo'}, 'foo'),
    ('<!--# if expr="$name" -->foo<!--# else -->bar<!--# endif -->', {}, 'bar'),
    ('<!--# if expr="$name = foo" -->foo<!--# elif expr="$name = bar" -->bar<!--# endif -->', {'name': 'bar'}, 'bar'),
    ('<!--# if expr="$name = foo" -->foo<!--# elif expr="$name = bar" -->bar<!--# else -->baz<!--# endif -->', {'name': 'baz'}, 'baz'),
    ('<!--# set var="name" value="foo" --><!--# echo var="name" -->', {}, 'foo'),
    ('<!--# include file="tests/resources/include.txt" -->', {}, 'foo'),
    ('<!--# include file="tests/resources/include.txt" set="name"--><!--# echo var="name" -->', {}, 'foo'),
    ('<!--# block name="name" -->foo<!--# endblock --><!--# include file="tests/resources/empty.txt" stub="name"-->', {}, 'foo'),
]


class ResponseMock(object):

    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return


class TestParser(object):

    def setup(self):
        self.parser = Parser()

    def test_evaluation(self):
        for test, context, expected in TESTS:
            ast = self.parser.parse(test)
            actual = ast.evaluate(context)
            assert actual == expected

    def test_include_simple_url(self):
        requests.get = MagicMock(return_value=ResponseMock('foo'))
        test = '<!--# include virtual="/foo" -->'
        ast = self.parser.parse(test)
        actual = ast.evaluate({})
        assert actual == 'foo'

    def test_include_set_var(self):
        requests.get = MagicMock(return_value=ResponseMock('foo'))
        test = '<!--# include virtual="/foo" set="name"--><!--# echo var="name" -->'
        ast = self.parser.parse(test)
        actual = ast.evaluate({})
        assert actual == 'foo'

    def test_include_empty_url(self):
        requests.get = MagicMock(return_value=ResponseMock(''))
        test = '<!--# block name="name" -->foo<!--# endblock --><!--# include virtual="/" stub="name"-->'
        ast = self.parser.parse(test)
        actual = ast.evaluate({})
        assert actual == 'foo'
