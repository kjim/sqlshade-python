# -*- coding: utf-8 -*-

def sorted_dict_repr(d):
    """repr() a dictionary with the keys in order.
    
    Used by the lexer unit test to compare parse trees based on strings.
    
    """
    keys = d.keys()
    keys.sort()
    return "{" + ", ".join(["%r: %r" % (k, d[k]) for k in keys]) + "}"
