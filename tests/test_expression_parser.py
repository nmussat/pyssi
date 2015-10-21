from pytest import raises
from pyssi import ExpressionParser
from pyparsing import ParseException


class TestExpresionParser(object):

    def setup(self):
        self.parser = ExpressionParser()

    def test_basic_expression(self):
        '''True if variable is defined'''
        actual = self.parser.parse('$name')
        assert actual.evaluate({'name': None})
        actual = self.parser.parse('$foo')
        assert not actual.evaluate({'name': None})

    def test_basic_comparaison(self):
        '''True if variable content is equal'''
        actual = self.parser.parse('$name = bar')
        assert actual.evaluate({'name': 'bar'})
        actual = self.parser.parse('$name = foo')
        assert not actual.evaluate({'name': 'bar'})
        actual = self.parser.parse('$name = foo')
        assert not actual.evaluate({'name': 'bar'})
        actual = self.parser.parse('$name != foo')
        assert actual.evaluate({'name': 'bar'})
        actual = self.parser.parse("$name = 'bar baz'")
        assert actual.evaluate({'name': 'bar baz'})
        actual = self.parser.parse("$name != 'foo fool'")
        assert actual.evaluate({'name': 'bar baz'})

    def test_regexp(self):
        actual = self.parser.parse('$name = /test[23]/')
        assert actual.evaluate({'name': 'test2'})
        assert actual.evaluate({'name': 'test3'})
        assert not actual.evaluate({'name': 'test4'})
        actual = self.parser.parse('$name != /test[23]/')
        assert actual.evaluate({'name': 'foo'})
        assert not actual.evaluate({'name': 'test2'})

    def test_regexp_fill_context(self):
        context = {'name': 'test@test.com'}
        actual = self.parser.parse('$name = /(.+)@(?P<domain>.+)/')
        actual.evaluate(context)
        assert 'domain' in context
        assert context['domain'] == 'test.com'

    def test_invalid_expression(self):
        with raises(ParseException):
            actual = self.parser.parse('name')
            actual.evaluate({'name': 'bar'})
        with raises(ParseException):
            actual = self.parser.parse('$name <> test')
