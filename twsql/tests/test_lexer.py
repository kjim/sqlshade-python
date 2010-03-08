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

    def test_nested_n_control_comment(self):
        query = """SELECT * FROM t_member WHERE TRUE
            /*#if :item*/
                /*#if :nested_item*/
                    /*#embed :embed_item*/
                    control comment allowed nest
                    /*#endembed*/
                /*#endif*/
            /*#endif*/
        """
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert nodes[0].text == """SELECT * FROM t_member WHERE TRUE
            """

        node_if = nodes[1]
        assert isinstance(node_if, tree.IfControl)
        assert node_if.ident == 'item'
        assert len(node_if.nodes) == 3

        node_nested_if = node_if.nodes[1]
        assert isinstance(node_nested_if, tree.IfControl)
        assert node_nested_if.ident == 'nested_item'
        assert len(node_nested_if.nodes) == 3

        node_embed = node_nested_if.nodes[1]
        assert isinstance(node_embed, tree.EmbedControl)
        assert node_embed.ident == 'embed_item'
        assert len(node_embed.nodes) == 1

        node_nested_literal = node_embed.nodes[0]
        assert isinstance(node_nested_literal, tree.Literal)
        assert node_nested_literal.text == """
                    control comment allowed nest
                    """

    def read_through(self, text):
        (stack, string, escape) = (0, False, False)
        for i, c in enumerate(text):
            if string is False:
                if c == '(':
                    stack += 1
                elif  c == ')':
                    stack -= 1
            if escape is False:
                if c == "'":
                    string = not string
                elif c == "\\":
                    escape = True
            else:
                escape = False
            if stack == 0:
                return i
        return -1

    def test_read_through(self):
        assert self.read_through("('foo')") == 6
        assert self.read_through("('foo)')") == 7
        assert self.read_through("('foo) \\'bar ')") == 14

        assert self.read_through("('foo', 'bar', 'baz')") == 20
        assert self.read_through("(1, 2, 3)") == 8
        assert self.read_through("(CURRENT_TIMESTAMP, now(), '2010-03-06 12:00:00')") == 48
