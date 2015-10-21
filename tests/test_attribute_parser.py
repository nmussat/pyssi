from pytest import raises
from pyssi import AttributeParser
from pyparsing import ParseException


class TestAttributesParser(object):

    def setup(self):
        self.parser = AttributeParser()

    def test_basic_attribute(self):
        actual = self.parser.parse('key="value" key2="value2"')
        assert 'key' in actual
        assert actual['key'] == 'value'
        assert 'key2' in actual
        assert actual['key2'] == 'value2'

    def test_unquoted_attribute(self):
        with raises(ParseException):
            self.parser.parse('key=value')

    def test_misbalanced_quotes(self):
        with raises(ParseException):
            self.parser.parse('key="value" foo="bar')

    def test_reusable_instance(self):
        actual = self.parser.parse('key="value"')
        assert 'key' in actual

        actual = self.parser.parse('foo="bar"')
        assert 'foo' in actual
        assert 'key' not in actual
