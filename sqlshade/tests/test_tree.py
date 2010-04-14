import unittest

from sqlshade import tree, exc

def wrap_node(nodecls, **g_kwargs):
    g_kwargs.setdefault('source', '')
    g_kwargs.setdefault('lineno', 1)
    g_kwargs.setdefault('pos', 1)
    g_kwargs.setdefault('filename', '')
    def node(*args):
        return nodecls(*args, **g_kwargs)
    return node

class DefinedControlCommentTest(unittest.TestCase):

    def test_for(self):
        for_comment = wrap_node(tree.ControlComment)('for', ' item in items ')
        assert for_comment.keyword == 'for'
        assert for_comment.item == 'item'
        assert for_comment.ident == 'items'

        for_comment = wrap_node(tree.ControlComment)('for', 'iter_item_value in iter_items')
        assert for_comment.item == 'iter_item_value'
        assert for_comment.ident == 'iter_items'

    def test_ident_for_for(self):
        for_comment = wrap_node(tree.ControlComment)('for', ' item in items')
        assert for_comment.ident == 'items'

        for_comment = wrap_node(tree.ControlComment)('for', ' item in container.items')
        assert for_comment.ident == 'container.items'

    def test_for_invalid_syntax(self):
        self.assertRaises(exc.SyntaxError, wrap_node(tree.ControlComment), *['for', ':item in items'])
        self.assertRaises(exc.SyntaxError, wrap_node(tree.ControlComment), *['for', ':items'])

    def test_if(self):
        if_comment = wrap_node(tree.ControlComment)('if', ' item')
        assert if_comment.keyword == 'if'
        assert if_comment.ident == 'item'

    def test_idnet_for_if(self):
        if_comment = wrap_node(tree.ControlComment)('if', ' item')
        assert if_comment.ident == 'item'

        if_comment = wrap_node(tree.ControlComment)('if', 'container.item')
        assert if_comment.ident == 'container.item'

    def test_if_invalid_syntax(self):
        self.assertRaises(exc.SyntaxError, wrap_node(tree.ControlComment), *['if', 'item == True'])
        self.assertRaises(exc.SyntaxError, wrap_node(tree.ControlComment), *['if', 'item is True'])

    def test_embed(self):
        embed_comment = wrap_node(tree.ControlComment)('embed', ' item')
        assert embed_comment.keyword == 'embed'
        assert embed_comment.ident == 'item'

    def test_ident_for_embed(self):
        embed_comment = wrap_node(tree.ControlComment)('embed', 'item')
        assert embed_comment.ident == 'item'

        embed_comment = wrap_node(tree.ControlComment)('embed', 'container.item')
        assert embed_comment.ident == 'container.item'

    def test_undefined_control(self):
        self.assertRaises(exc.CompileError, wrap_node(tree.ControlComment), *['undefined', 'arg'])
        self.assertRaises(exc.CompileError, wrap_node(tree.ControlComment), *['forin', 'arg'])


class CommentTest(unittest.TestCase):

    def test_comment(self):
        block_comment = wrap_node(tree.Comment)(' this is a really comment ', True)
        assert block_comment.text == ' this is a really comment '
        assert block_comment.is_block == True

        line_comment = wrap_node(tree.Comment)('this is a line comment', False)
        assert line_comment.text == 'this is a line comment'
        assert line_comment.is_block == False
