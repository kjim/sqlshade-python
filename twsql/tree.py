# -*- coding: utf-8 -*-

"""defines the parse tree components for twsql templates."""

from twsql import util

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

class ControlLine(Node):
    """defines a control line, a line-oriented python line or end tag.
    
    e.g.::

        /*#enabled :foo*/
            (markup)
        /*#/enabled*/
    
    """

    def __init__(self, keyword, isend, text, **kwargs):
        super(ControlLine, self).__init__(**kwargs)
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

    def __init__(self, content, **kwargs):
        super(Literal, self).__init__(**kwargs)
        self.content = content

    def __repr__(self):
        return "Text(%r, %r)" % (self.content, (self.lineno, self.pos))

class Comment(Node):
    """defines a comment line.
    
    /* this is a comment */

    -- this is also a comment
    
    """

    def __init__(self, text, **kwargs):
        super(Comment, self).__init__(**kwargs)
        self.text = text

    def __repr__(self):
        return "Comment(%r, %r)" % (self.text, (self.lineno, self.pos))
