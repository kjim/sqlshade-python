import unittest
import pprint

from twsql import lexer, tree, exc

pp = pprint.PrettyPrinter()

class LexerTest(unittest.TestCase):

    def parse(self, sql):
        lex = lexer.Lexer(sql)
        node = lex.parse()
        return node.nodes

    def test_embed(self):
        query = """SELECT ident /*identifier*/ FROM t_member WHERE /*#embed :item*/t_member.age = 25/*#/embed*/;"""
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert nodes[0].text == 'SELECT ident '

        assert isinstance(nodes[1], tree.Comment)
        assert nodes[1].text == 'identifier'

        assert isinstance(nodes[2], tree.Literal)
        assert nodes[2].text == ' FROM t_member WHERE '

        assert isinstance(nodes[3], tree.Embed)
        assert nodes[3].ident == 'item'
        assert len(nodes[3].nodes) == 1
        embed_child = nodes[3].nodes[0]
        assert isinstance(embed_child, tree.Literal)
        assert embed_child.text == 't_member.age = 25'

    def test_eval(self):
        query = """SELECT * FROM t_member WHERE /*#eval :item*/t_member.age = 25/*#/eval*/;"""
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert isinstance(nodes[1], tree.Eval)
        assert isinstance(nodes[2], tree.Literal)
        assert nodes[1].ident == 'item'
        assert len(nodes[1].nodes) == 1
        eval_child = nodes[1].nodes[0]
        assert isinstance(eval_child, tree.Literal)
        assert eval_child.text == 't_member.age = 25'

    def test_for(self):
        query = """SELECT * FROM t_member WHERE /*#for item in :items*/ /* inner */ /* literal here */ /*#/for*/"""
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert nodes[0].text == 'SELECT * FROM t_member WHERE '

        assert isinstance(nodes[1], tree.For)
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

        assert isinstance(nodes[1], tree.If)
        assert nodes[1].ident == 'item'
        assert len(nodes[1].nodes) == 1
        children = nodes[1].nodes
        assert children[0].text == 'WHERE id = 232'

    def test_nested_n_control_comment(self):
        query = """SELECT * FROM t_member WHERE TRUE
            /*#if :item*/
                /*#if :nested_item*/
                    /*#embed :embed_item*/AND TRUE/*#endembed*/
                    AND keyword = /*:keyword*/'test keyword'
                /*#endif*/
            /*#endif*/
        """
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert nodes[0].text == """SELECT * FROM t_member WHERE TRUE
            """

        node_if = nodes[1]
        assert isinstance(node_if, tree.If)
        assert node_if.ident == 'item'
        assert len(node_if.nodes) == 3

        node_nested_if = node_if.nodes[1]
        assert isinstance(node_nested_if, tree.If)
        assert node_nested_if.ident == 'nested_item'
        assert len(node_nested_if.nodes) == 5

        node_embed = node_nested_if.nodes[1]
        assert isinstance(node_embed, tree.Embed)
        assert node_embed.ident == 'embed_item'
        assert len(node_embed.nodes) == 1

        node_nested_literal = node_embed.nodes[0]
        assert isinstance(node_nested_literal, tree.Literal)
        assert node_nested_literal.text == "AND TRUE"

        node_substitute = node_nested_if.nodes[3]
        assert isinstance(node_substitute, tree.SubstituteComment)
        assert node_substitute.ident == 'keyword'
        assert node_substitute.text == "'test keyword'"

    def test_substitute_string(self):
        query = """SELECT * FROM t_member WHERE id = /*:id*/'UUID'"""
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert nodes[0].text == """SELECT * FROM t_member WHERE id = """

        assert isinstance(nodes[1], tree.SubstituteComment)
        assert nodes[1].ident == 'id'
        assert nodes[1].text == "'UUID'"

    def test_substitute_contained_linefeed_string(self):
        query = """SELECT * FROM t_member
            WHERE
                true
                AND id = /*:id*/'this is fake value
this line is fake value too.'
            """
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert isinstance(nodes[1], tree.SubstituteComment)
        assert nodes[1].ident == 'id'
        assert nodes[1].text == """'this is fake value
this line is fake value too.'"""

        assert isinstance(nodes[2], tree.Literal)

    def test_substitute_paren(self):
        query = """SELECT * FROM t_member WHERE id IN /*:ids*/('mc', 'mos', CONCAT('mis', 'do'))/* comment */"""
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert isinstance(nodes[1], tree.SubstituteComment)
        assert isinstance(nodes[2], tree.Comment)
        assert nodes[1].ident == 'ids'
        assert nodes[1].text == "('mc', 'mos', CONCAT('mis', 'do'))"

    def test_substitute_contained_linefeed_in_paren_params(self):
        # case 1
        query = """SELECT * FROM t_member
            WHERE
                true
                AND id IN /*:ids*/('this is fake value
this line is fake value too.
                ', 'params2', 'params3')
            """
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert isinstance(nodes[1], tree.SubstituteComment)
        assert isinstance(nodes[2], tree.Literal)
        assert nodes[1].ident == 'ids'
        assert nodes[1].text == """('this is fake value
this line is fake value too.
                ', 'params2', 'params3')"""

        # case 2
        query = """SELECT * FROM t_member
            WHERE
                true
                AND id IN /*:ids*/(
                    'first'
                    , 'second'
                    , 'third'
                )
                AND status IN /*:available_status_list*/(1, 10, 100, 10.33)
            """
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert isinstance(nodes[1], tree.SubstituteComment)
        assert isinstance(nodes[2], tree.Literal)
        assert isinstance(nodes[3], tree.SubstituteComment)
        assert isinstance(nodes[4], tree.Literal)

        assert nodes[1].ident == 'ids'
        assert nodes[1].text == """(
                    'first'
                    , 'second'
                    , 'third'
                )"""
        assert nodes[3].ident == 'available_status_list'
        assert nodes[3].text == '(1, 10, 100, 10.33)'

    def test_substitute_subquery(self):
        query = """SELECT * FROM t_member
            WHERE
                id = /*:id*/(
                    select 1
                )
            """
        nodes = self.parse(query)

        assert isinstance(nodes[0], tree.Literal)
        assert isinstance(nodes[1], tree.SubstituteComment)
        assert isinstance(nodes[2], tree.Literal)
        assert nodes[1].ident == 'id'
        assert nodes[1].text == """(
                    select 1
                )"""

    def test_ident_rule_for_substitute(self):
        nodes = self.parse("simple = /*:simple*/'test word'")
        assert isinstance(nodes[0], tree.Literal)
        assert isinstance(nodes[1], tree.SubstituteComment)
        assert nodes[1].ident == 'simple'

        nodes = self.parse("dotaccess = /*:dotaccess.data*/'test word'")
        assert isinstance(nodes[0], tree.Literal)
        assert isinstance(nodes[1], tree.SubstituteComment)
        assert nodes[1].ident == 'dotaccess.data'

    def test_raise_on_substitute(self):
        self.assertRaises(exc.SyntaxError, self.parse, """SELECT * FROM t_member WHERE id in /*:ids*/(12, 32, 23""")
        self.assertRaises(exc.SyntaxError, self.parse, """SELECT * FROM t_member WHERE id = /*:id*/'""")

    def test_parse_until_end_of_sqlword(self):
        parse = lexer.Lexer.parse_until_end_of_sqlword
        should_be_close_paren = ")"

        assert parse("('foo')") == 7
        assert parse("('foo)')") == 8
        assert parse("('foo) \\'bar ')") == 15

        assert parse("('foo', 'bar', 'baz')") == 21
        assert parse("(1, 2, 3)") == 9
        assert parse("(CURRENT_TIMESTAMP, now(), '2010-03-06 12:00:00')") == 49

        assert parse("CURRENT_TIMESTAMP") == 17
        assert parse("now()") == 5
        assert parse("(cast('323' as Number), to_int(now())) and", should_be_close_paren) == 38

        assert parse("0") == 1
        assert parse("12345") == 5
        assert parse("+12345") == 6
        assert parse("-12345") == 6

        assert parse("") == -1
        assert parse(" ") == -1
        assert parse("(") == -1
        assert parse(")") == -1
        assert parse("()", should_be_close_paren) == 2
