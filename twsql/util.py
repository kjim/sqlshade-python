# -*- coding: utf-8 -*-

def sorted_dict_repr(d):
    """repr() a dictionary with the keys in order.
    
    Used by the lexer unit test to compare parse trees based on strings.
    
    """
    keys = d.keys()
    keys.sort()
    return "{" + ", ".join(["%r: %r" % (k, d[k]) for k in keys]) + "}"

class FastEncodingBuffer(object):
    """a very rudimentary buffer that is faster than StringIO, but doesnt crash on unicode data like cStringIO."""

    def __init__(self, encoding=None, errors='strict', unicode=False):
        self.data = []
        self.encoding = encoding
        if unicode:
            self.delim = u''
        else:
            self.delim = ''
        self.unicode = unicode
        self.errors = errors
        self.write = self.data.append

    def getvalue(self):
        if self.encoding:
            return self.delim.join(self.data).encode(self.encoding, self.errors)
        else:
            return self.delim.join(self.data)
