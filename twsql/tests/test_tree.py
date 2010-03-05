import unittest

from twsql import tree, exc

def ControlComment(keyword, text, **kwargs):
    kwargs.setdefault('source', '')
    kwargs.setdefault('lineno', 1)
    kwargs.setdefault('pos', 1)
    kwargs.setdefault('filename', '')
    return tree.ControlComment(keyword, text, **kwargs)

class DefinedControlCommentTest(unittest.TestCase):

    def test_for(self):
        for_comment = ControlComment('for', ' item in :items ')
        assert for_comment.keyword == 'for'
        assert for_comment.item == 'item'
        assert for_comment.ident == 'items'

        for_comment = ControlComment('for', 'iter_item_value in :iter_items')
        assert for_comment.item == 'iter_item_value'
        assert for_comment.ident == 'iter_items'

    def test_for_invalid_syntax(self):
        self.assertRaises(exc.CompileError, ControlComment, *['for', ':item in :items'])
        self.assertRaises(exc.CompileError, ControlComment, *['for', ':items'])

    def test_if(self):
        if_comment = ControlComment('if', ' :item')
        assert if_comment.keyword == 'if'
        assert if_comment.ident == 'item'

    def test_if_invalid_syntax(self):
        self.assertRaises(exc.CompileError, ControlComment, *['if', 'item'])
        self.assertRaises(exc.CompileError, ControlComment, *['if', ':item == True'])
        self.assertRaises(exc.CompileError, ControlComment, *['if', ':item is True'])

    def test_embed(self):
        embed_comment = ControlComment('embed', ' :item')
        assert embed_comment.keyword == 'embed'
        assert embed_comment.ident == 'item'

    def test_embed_invalid_syntax(self):
        self.assertRaises(exc.CompileError, ControlComment, *['embed', 'boolean_item'])

    def test_undefined_control(self):
        self.assertRaises(exc.CompileError, ControlComment, *['undefined', 'arg'])
        self.assertRaises(exc.CompileError, ControlComment, *['forin', 'arg'])
