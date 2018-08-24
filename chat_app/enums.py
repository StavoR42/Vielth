# coding: utf-8


class BaseEnumerate(object):
    values = {}

    @classmethod
    def get_choices(cls):
        return ((k, v) for k, v in cls.values.items())


class BaseDict(object):
    pass


########################################################################################################################


class BracesDict(BaseDict):
    """Словарь со скобками"""
    BRACE_OPEN = '{'
    BRACE_CLOSE = '}'
    PARENTHESIS_OPEN = '('
    PARENTHESIS_CLOSE = ')'
    SQUARE_OPEN = '['
    SQUARE_CLOSE = ']'

    BRACES = (BRACE_OPEN, BRACE_CLOSE)
    PARENTHESES = [PARENTHESIS_OPEN, PARENTHESIS_CLOSE]
    SQUARES = (SQUARE_OPEN, SQUARE_CLOSE)

    OPENERS = (BRACE_OPEN, PARENTHESIS_OPEN, SQUARE_OPEN)
    CLOSERS = (BRACE_CLOSE, PARENTHESIS_CLOSE, SQUARE_CLOSE)

    ALL = (BRACE_OPEN, BRACE_CLOSE, PARENTHESIS_OPEN, PARENTHESIS_CLOSE, SQUARE_OPEN, SQUARE_CLOSE)