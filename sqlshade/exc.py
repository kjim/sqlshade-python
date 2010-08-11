# -*- coding: utf-8 -*-

"""exception classes"""

class Error(Exception):
    pass

class RenderError(Error):
    pass

class ArgumentError(Error):
    pass

def _format_filepos(lineno, pos, filename):
    if filename is None:
        return " at line: %d char: %d" % (lineno, pos)
    else:
        return " in file '%s' at line: %d char: %d" % (filename, lineno, pos)

class CompileError(Error):
    def __init__(self, message, source, lineno, pos, filename):
        Error.__init__(self, message + _format_filepos(lineno, pos, filename))
        self.lineno =lineno
        self.pos = pos
        self.filename = filename
        self.source = source

class SyntaxError(Error):
    def __init__(self, message, source, lineno, pos, filename):
        Error.__init__(self, message + _format_filepos(lineno, pos, filename))
        self.lineno =lineno
        self.pos = pos
        self.filename = filename
        self.source = source
