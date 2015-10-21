''' SSI instruction parser

    block<name> endblock
    config<errmsg, timefmt>
    echo<var (encoding default)>
    if<expr> endif
    if<expr> else<expr> endif
    if<expr> elif<expr> endif
    include<file (stub wait set)>
    include<virtual (stub wait set)>
    set<var value>
    default context = date_local, date_gmt
'''

import re
import requests
import string

from operator import eq, ne
from pyparsing import Group, Literal, OneOrMore, Word, \
    dblQuotedString, QuotedString, removeQuotes


def evaluate_tokens(tokens, context):
    '''Evaluate every tokens according to a context and returns a string'''
    result = [token.evaluate(context) for token in tokens if token]
    return ''.join(filter(None, result))


class Node(object):

    end_tags = None
    _children = None

    def __init__(self, attributes=None):
        self.attributes = attributes
        self._children = []

    @property
    def children(self):
        return self._children

    @children.setter
    def children(self, value):
        self._children.append(value)

    def __repr__(self):
        return str([self.__class__.__name__, self.attributes, self.children])

    def evaluate(self, context):
        return evaluate_tokens(self.children, context)


class Noop(Node):
    '''Empty Node used to account for end tags'''
    pass


class Text(Node):
    '''Represents nodes which aren't SSI instruction'''

    def evaluate(self, context):
        return self.attributes


class Block(Node):
    '''A lazy-evaluated instruction to use as content for echo instructions'''

    end_tags = {'ENDBLOCK'}

    def evaluate(self, context):
        name = self.attributes['name']
        context[name] = lambda: evaluate_tokens(self.children, context)


class Endblock(Node):
    pass


class Config(Node):
    '''Updates the evaluation context'''

    def evaluate(self, context):
        context.update(self.attributes)


class Echo(Node):
    '''Emit a variable from the context or a block'''

    def evaluate(self, context):
        # TODO encoding
        var = self.attributes['var']
        try:
            value = context[var]
            if callable(value):
                return value()
            return value
        except KeyError as err:
            if 'default' in self.attributes:
                return self.attributes['default']
            return context.get('errmsg', '[an error occurred while processing the directive]')


class If(Node):
    '''Implements logic in SSI instructions'''

    end_tags = {'ELIF', 'ELSE', 'ENDIF'}
    _children = None
    _else_tokens = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._else_tokens = []

    def __repr__(self):
        return str([self.__class__.__name__, self.attributes,
                   self.children, self._else_tokens])

    @property
    def children(self):
        return self._children

    @children.setter
    def children(self, value):
        if isinstance(value, (Elif, Else)):
            self._else_tokens.append(value)
        else:
            self._children.append(value)

    def evaluate(self, context):
        expression = ExpressionParser().parse(self.attributes['expr'])
        if expression.evaluate(context):
            return evaluate_tokens(self._children, context)
        elif self._else_tokens:
            return evaluate_tokens(self._else_tokens, context)


class Elif(If):
    '''Implements `Else if` logic'''

    end_tags = {'ELSE', 'ENDIF'}


class Else(Node):
    '''Implements `Else` logic'''

    end_tags = {'ENDIF'}


class Endif(Node):
    pass


class Include(Node):
    '''Include content from a file or an url'''

    def _get_file(self, file):
        # TODO root dir parameter and security
        with open(file, 'r') as f:
            return f.read().strip()

    def _get_url(self, url):
        # TODO Pass url root through
        response = requests.get(url)
        response.raise_for_status()
        return response.text

    def evaluate(self, context):
        file = self.attributes.get('file')
        url = self.attributes.get('virtual')
        if all([file, url]) or not any([file, url]):
            raise Exception('Include must declare either \
                    a file or a virtual attribute')
        if file:
            content = self._get_file(file)
        if url:
            content = self._get_url(url)
        set_ = self.attributes.get('set')
        if set_:
            context[set_] = content
            return
        stub = self.attributes.get('stub')
        if not content and stub:
            block = context[stub]
            if callable(block):
                return block()
            return block
        return content


class Set(Node):

    def evaluate(self, context):
        var = self.attributes['var']
        value = self.attributes['value']
        # TODO: evaluate value
        context[var] = value


def token_factory(name, attributes):
    map = {
        'TEXT': Text,
        'BLOCK': Block,
        'ENDBLOCK': Endblock,
        'CONFIG': Config,
        'ECHO': Echo,
        'IF': If,
        'ELIF': Elif,
        'ELSE': Else,
        'ENDIF': Endif,
        'INCLUDE': Include,
        'SET': Set,
    }
    return map[name](attributes)


class AttributeParser(object):

    name = Word(string.ascii_lowercase + string.digits + '$_-')
    sep = Literal('=').suppress()
    value = dblQuotedString().setParseAction(removeQuotes)
    attributes = OneOrMore(Group(name + sep + value))

    def parse(self, text):
        result = self.attributes.parseString(text, parseAll=True)
        return {k: v for k, v in result}


class ExpressionEvaluationError(Exception):
    pass


class Expression(object):

    def __init__(self, tokens):
        self.tokens = tokens

    def _get_operator_func(self, operator):
        if operator == '=':
            return eq
        elif operator == '!=':
            return ne
        raise ExpressionEvaluationError

    def evaluate(self, context):
        variable = self.tokens.get('variable')
        # Parser returns a list of list for this token
        if variable:
            variable = variable[0]
        operator = self.tokens.get('operator')
        text = self.tokens.get('text')
        regexp = self.tokens.get('regexp')

        if regexp:
            match = re.match(regexp, context.get(variable, ''))
            op_func = self._get_operator_func(operator)
            result = op_func(match is not None, True)
            if result and match:
                context.update(match.groupdict({}))
            return result
        elif text:
            op_func = self._get_operator_func(operator)
            return op_func(context.get(variable), text)
        elif variable:
            return variable in context
        else:
            raise ExpressionEvaluationError


class ExpressionParser(object):

    word = Word(string.ascii_lowercase + '_')
    variable = Group(Literal('$').suppress() + word).setResultsName('variable')
    _text = QuotedString(quoteChar="'", unquoteResults=True)
    text = (_text | Word(string.printable)).setResultsName('text')
    regexp = QuotedString(quoteChar='/', unquoteResults=True)('regexp')
    equal = Literal('=')
    not_equal = Literal('!=')
    operator = (equal | not_equal).setResultsName('operator')
    expression = (variable + operator + regexp) | (variable + operator + text) | variable

    def parse(self, text):
        expr = self.expression.parseString(text, parseAll=True)
        return Expression(expr)


class Parser(object):

    def __init__(self):
        self.attribute_parser = AttributeParser()

    def parse(self, text):
        return self.build_ast(self.lexemize(text))

    def lexemize(self, text):
        pos = 0
        start_delimiter = '<!--#'
        end_delimiter = '-->'
        while True:
            try:
                offset = text.index(start_delimiter, pos)
                value = text[pos:offset]
                if value:
                    yield ('TEXT', value)
                pos = offset + len(start_delimiter)
            except ValueError:
                value = text[pos:]
                if value:
                    yield ('TEXT', value)
                break
            try:
                offset = text.index(end_delimiter, pos)
                value = text[pos:offset]
                if value:
                    yield self.tokenize(value)
                pos = offset + len(end_delimiter)
            except ValueError:
                raise Exception('End marker not found')

    def tokenize(self, expression):
        expression = expression.strip()
        if ' ' not in expression:
            return (expression.upper(), None)
        verb, attr_text = expression.split(maxsplit=1)
        attributes = self.attribute_parser.parse(attr_text)
        return (verb.upper(), attributes)

    def build_ast(self, tokens):
        head = Node()

        def inner(root, tokens):
            for token in tokens:
                name, attributes = token
                node = token_factory(name, attributes)
                if node.end_tags:
                    root.children = node
                    inner(node, tokens)
                    continue
                if root.end_tags and name in root.end_tags:
                    return
                root.children = node

        inner(head, iter(tokens))
        return head
