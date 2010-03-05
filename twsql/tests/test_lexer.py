import unittest
import pprint

from twsql import lexer, tree

pp = pprint.PrettyPrinter()

class LexerTest(unittest.TestCase):

    def parse(self, sql):
        lex = lexer.Lexer(sql)
        lex.parse()
        return lex.template.nodes

    def test_embed(self):
        query = """SELECT ident /*identifier*/ FROM t_member WHERE /*#embed :item*/t_member.age = 25/*#/embed*/;"""
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert nodes[0].text == 'SELECT ident '

        assert isinstance(nodes[1], tree.Comment)
        assert nodes[1].text == 'identifier'

        assert isinstance(nodes[2], tree.Literal)
        assert nodes[2].text == ' FROM t_member WHERE '

        assert isinstance(nodes[3], tree.EmbedControl)
        assert nodes[3].ident == 'item'
        assert len(nodes[3].nodes) == 1
        embed_child = nodes[3].nodes[0]
        assert isinstance(embed_child, tree.Literal)
        assert embed_child.text == 't_member.age = 25'

    def test_for(self):
        query = """SELECT * FROM t_member WHERE /*#for item in :items*/ /* inner */ /* literal here */ /*#/for*/"""
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert nodes[0].text == 'SELECT * FROM t_member WHERE '

        assert isinstance(nodes[1], tree.ForControl)
        assert nodes[1].item == 'item'
        assert nodes[1].ident == 'items'
        assert len(nodes[1].nodes) == 5
        children = nodes[1].nodes
        assert children[0].text == ' '
        assert children[1].text == ' inner '
        assert children[2].text == ' '
        assert children[3].text == ' literal here '
        assert children[4].text == ' '

    def test_if(self):
        query = """SELECT * FROM t_member /*#if :item*/WHERE id = 232/*#/if*/"""
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert nodes[0].text == 'SELECT * FROM t_member '

        assert isinstance(nodes[1], tree.IfControl)
        assert nodes[1].ident == 'item'
        assert len(nodes[1].nodes) == 1
        children = nodes[1].nodes
        assert children[0].text == 'WHERE id = 232'
