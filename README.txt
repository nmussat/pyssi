pyssi
=====


Purpose
-------

Implements an Nginx-compatible SSI parser and interpreter in Python.
It's useful to debug your SSI application without an Nginx frontend.

Production usage is not recommended for performance reason.


Installation
------------

```python
pip install pyssi
```

Usage
-----

```python
from pyssi import Parser

parser = Parser()
ast = parser.parse('<!--# echo var="name" -->')
print(ast.evaluate({'var': 'foo'})
```


UnitTests
---------

Clone the repository and run `python setup.py test`.
