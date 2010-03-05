import unittest

from twsql import tree

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

    def test_if(self):
        if_comment = ControlComment('if', ' :item')
        assert if_comment.keyword == 'if'
        assert if_comment.ident == 'item'

    def test_embed(self):
        embed_comment = ControlComment('embed', ' :item')
        assert embed_comment.keyword == 'embed'
        assert embed_comment.ident == 'item'
