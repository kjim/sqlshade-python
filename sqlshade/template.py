# -*- coding: utf-8 -*-
import re

from sqlshade.lexer import Lexer
from sqlshade import exc, sqlgen

class Template(object):

    def __init__(self,
                 text=None,
                 filename=None,
                 input_encoding=None,
                 output_encoding=None,
                 disable_unicode=False,
                 strict=True):
        if filename:
            self.module_id = re.sub(r'\W', '_', filename)
            self.uri = filename
        else:
            self.module_id = "memory:" + hex(id(self))
            self.uri = self.module_id

        self.input_encoding = input_encoding
        self.output_encoding = output_encoding
        self.disable_unicode = disable_unicode
        self.strict = strict

        if text is not None:
            node = _compile_text(self, text, filename)
            self.node = node
        else:
            raise exc.RuntimeError("Template requires text or filename")

        self.filename = filename

    def render(self, **context):
        return sqlgen.compile(self.node, self.filename, context,
                              source_encoding=self.input_encoding,
                              generate_unicode=self.disable_unicode is False,
                              strict=self.strict
                              )

def _compile_text(template, text, filename):
    id = template.module_id
    lexer = Lexer(text, filename,
        disable_unicode=template.disable_unicode,
        input_encoding=template.input_encoding
    )
    node = lexer.parse()
    return node
