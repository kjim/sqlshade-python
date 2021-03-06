# -*- coding: utf-8 -*-

"""defines the parse tree components for sqlshade templates."""

from sqlshade import util, exc

import re

class Node(object):
    """base class for a Node in the parse tree."""
    def __init__(self, source, lineno, pos, filename):
        self.source = source
        self.lineno = lineno
        self.pos = pos
        self.filename = filename

    @property
    def exception_kwargs(self):
        return {'source': self.source, 'lineno': self.lineno, 'pos': self.pos, 'filename': self.filename}

    def get_children(self):
        return []

    def accept_visitor(self, visitor, context):
        def traverse(node, context):
            for n in node.get_children():
                n.accept_visitor(visitor, context)
        method = getattr(visitor, "visit" + self.__class__.__name__ + '_' + context.mode, traverse)
        method(self, context)

class TemplateNode(Node):
    """a 'container' node that stores the overall collection of nodes."""

    def __init__(self, filename):
        super(TemplateNode, self).__init__('', 0, 0, filename)
        self.nodes = []
        self.page_attributes = {}

    def get_children(self):
        return self.nodes

    def __repr__(self):
        return "TemplateNode(%s, %r)" % (util.sorted_dict_repr(self.page_attributes), self.nodes)

class Literal(Node):
    """defines literal in the template."""

    def __init__(self, text, **kwargs):
        super(Literal, self).__init__(**kwargs)
        self.text = text

    def __repr__(self):
        return "Literal(%r, %r)" % (self.text, (self.lineno, self.pos))

class Comment(Node):
    """defines a comment line.
    
    /* this is a comment */
    
    -- this is also a comment
    
    """

    def __init__(self, text, is_block, **kwargs):
        super(Comment, self).__init__(**kwargs)
        self.text = text
        self.is_block = is_block

    def __repr__(self):
        return "Comment(%r, %r)" % ((self.text, self.is_block), (self.lineno, self.pos))

class SubstituteComment(Node):
    """substitute to placeholder.

    /*:string_item*/'string fake value'
    /*:number_item*/3000.00
    /*:array_item*/('mc', 'mos', 'misdo')

    """

    def __init__(self, ident, text, **kwargs):
        super(SubstituteComment, self).__init__(**kwargs)
        self.ident = ident
        self.text = text

    def __repr__(self):
        return "SubstituteComment(%r, %r)" % ((self.ident, self.text), (self.lineno, self.pos))

class _ControlCommentMeta(type):
    """metaclass to allow control comment to produce a subclass according to its keyword"""

    _classmap = {}

    def __init__(cls, clsname, bases, dict):
        if cls.__keyword__ is not None:
            cls._classmap[cls.__keyword__] = cls
            super(_ControlCommentMeta, cls).__init__(clsname, bases, dict)

    def __call__(cls, keyword, text, **kwargs):
        try:
            cls = _ControlCommentMeta._classmap[keyword]
        except KeyError:
            raise exc.CompileError("No such Control: '%s'" % keyword,
                source=kwargs['source'],
                lineno=kwargs['lineno'],
                pos=kwargs['pos'],
                filename=kwargs['filename']
            )
        return type.__call__(cls, keyword, text, **kwargs)

class ControlComment(Node):
    """abstract base class for comments.
    
    /*#for item in items*/
        (markup)
    /*#/for*/
    
    """

    __metaclass__ = _ControlCommentMeta
    __keyword__ = None

    def __init__(self, keyword, text, **kwargs):
        """construct a new Tag instance.
        
        this constructor not called directly, and is only called by subclasses.
        
        keyword - the control keyword

        text - the control argument text
        
        **kwargs - other arguments passed to the Node superclass (lineno, pos)
        
        """
        super(ControlComment, self).__init__(**kwargs)
        self.keyword = keyword
        self.text = text
        self.parent = None
        self.nodes = []

    def is_root(self):
        return self.parent is None

    def get_children(self):
        return self.nodes

    def __repr__(self):
        return "%s(%r, %s, %r, %r)" % (self.__class__.__name__,
                                        self.keyword,
                                        self.text,
                                        (self.lineno, self.pos),
                                        [repr(x) for x in self.nodes]
                                    )

class For(ControlComment):
    __keyword__ = 'for'

    for_pattern = r"""^\s* (\w+) \s+ in \s+ ([\w.]+) \s*$"""
    for_reg = re.compile(for_pattern, re.X)

    def __init__(self, keyword, text, **kwargs):
        super(For, self).__init__(keyword, text, **kwargs)
        match = self.for_reg.match(text)
        if match is None:
            raise exc.SyntaxError("for syntax is 'for <item> in <ident>'", **self.exception_kwargs)
        (self.item, self.ident) = (match.group(1), match.group(2))

class If(ControlComment):
    __keyword__ = 'if'

    if_pattern = r"""^\s* ([\w.]+) \s*$"""
    if_reg = re.compile(if_pattern, re.X)

    def __init__(self, keyword, text, **kwargs):
        super(If, self).__init__(keyword, text, **kwargs)
        match = self.if_reg.match(text)
        if match is None:
            raise exc.SyntaxError("if syntax is 'if <ident>'", **self.exception_kwargs)
        self.ident = match.group(1)

class Embed(ControlComment):
    __keyword__ = 'embed'

    embed_pattern = r"""^\s* ([\w.]+) \s*$"""
    embed_reg = re.compile(embed_pattern, re.X)

    def __init__(self, keyword, text, **kwargs):
        super(Embed, self).__init__(keyword, text, **kwargs)
        match = self.embed_reg.match(text)
        if match is None:
            raise exc.SyntaxError("embed syntax is 'embed <ident>'", **self.exception_kwargs)
        self.ident = match.group(1)

class Tip(ControlComment):
    __keyword__ = 'tip'

    def __init__(self, keyword, text='', **kwargs):
        super(Tip, self).__init__(keyword, '', **kwargs)
