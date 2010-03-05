# -*- coding: utf-8 -*-

"""defines the parse tree components for twsql templates."""

from twsql import util, exc

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

    def accept_visitor(self, visitor):
        def traverse(node):
            for n in node.get_children():
                n.accept_visitor(visitor)
        method = getattr(visitor, "visit" + self.__class__.__name__, traverse)
        method(self)

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

class ControlComment(Node):
    """defines a control line, a line-oriented python line or end tag.
    
    e.g.::

        /*#if :foo*/
            (markup)
        /*#/if*/
    
    """

    def __init__(self, keyword, isend, text, **kwargs):
        super(ControlComment, self).__init__(**kwargs)
        self.keyword = keyword
        self.text = text
        self.isend = isend
        self.is_primary = keyword in ['for','enabled', 'embed']

    def is_ternary(self, keyword):
        """return true if the given keyword is a ternary keyword for this ControlLine"""
        return []

    def __repr__(self):
        return "ControlLine(%r, %r, %r, %r)" % (
            self.keyword,
            self.text,
            self.isend,
            (self.lineno, self.pos)
        )

class Literal(Node):
    """defines literal in the template."""

    def __init__(self, text, **kwargs):
        super(Literal, self).__init__(**kwargs)
        self.text = text

    def __repr__(self):
        return "Literal(%r, %r)" % (self.content, (self.lineno, self.pos))

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
        return "Comment(%r, %r)" % (self.text, self.is_block), (self.lineno, self.pos))

class _ControlCommentMeta(type):
    """metaclass to allow Tag to produce a subclass according to its keyword"""

    _classmap = {}

    def __init__(cls, clsname, bases, dict):
        if cls.__keyword__ is not None:
            cls._classmap[cls.__keyword__] = cls
            super(_ControlCommentMeta, cls).__init__(clsname, bases, dict)

    def __call__(cls, keyword, text, **kwargs):
        try:
            cls = _ControlCommentMeta._classmap[keyword]
        except KeyError:
            raise exc.CompileException(
                "No such Control: '%s'" % keyword,
                source=kwargs['source'],
                lineno=kwargs['lineno'],
                pos=kwargs['pos'],
                filename=kwargs['filename']
            )
        return type.__call__(cls, keyword, text, **kwargs)

class ControlComment(Node):
    """abstract base class for tags.
    
    /*#for item in :items*/
        (markup)
    /*#/for*/
    
    """

    __metaclass__ = _ControlCommentMeta
    __keyword__ = None

    def __init__(self, keyword, text, **kwargs):
        """construct a new Tag instance.
        
        this constructor not called directly, and is only called by subclasses.
        
        keyword - the tag keyword
        
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

class ForControl(ControlComment):
    __keyword__ = 'for'

    for_pattern = r"""\s* (\w+) \s+ :(\w+)\s*"""
    for_reg = re.compile(for_pattern, re.X)

    def __init__(self, keyword, text, **kwargs):
        super(ForControl, self).__init__(keyword, text, ('file', 'import', 'args'), (), ('file',), **kwargs)
        match = self.for_reg.match(text)
        if match is None:
            raise exc.CompileException("for syntax is 'for <item> in <ident>'", **self.exception_kwargs)
        self.iteritem = match.group(1)
        self.items = match.group(2)

class IfControl(ControlComment):
    __keyword__ = 'if'

    if_pattern = r"""\s* :(\w+) \s*"""
    if_reg = re.compile(if_pattern, re.X)

    def __init__(self, keyword, text, **kwargs):
        super(IfControl, self).__init__(keyword, text, (), ('name','inheritable','file','import','module'), (), **kwargs)
        match = self.if_reg.match(text)

class EmbedControl(ControlComment):
    __keyword__ = 'embed'

    def __init__(self, keyword, text, **kwargs):
        super(EmbedControl, self).__init__(keyword, text, (), ('filter'), (), **kwargs)
