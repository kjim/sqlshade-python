import unittest

from twsql import sqlgen, tree

def NodeType(nodecls, **g_kwargs):
    g_kwargs.setdefault('source', '')
    g_kwargs.setdefault('lineno', 1)
    g_kwargs.setdefault('pos', 1)
    g_kwargs.setdefault('filename', '')
    def node(*args):
        return nodecls(*args, **g_kwargs)
    return node

class QueryCompilationTest(unittest.TestCase):

    def setUp(self):
        self.fname = 'compilation_test.sql'

    def compile(self, node, data=None):
        return sqlgen.compile(node, self.fname, data or {})

    def test_compile_literal_node(self):
        root = tree.TemplateNode(self.fname)
        root.nodes.append(NodeType(tree.Literal)('SELECT * FROM t_member;'))
        compiled = self.compile(root)
        assert compiled.sql == 'SELECT * FROM t_member;'
        assert compiled.bound_variables == []

    def test_compile_substitute_scalar_node(self):
        root = tree.TemplateNode(self.fname)
        node = NodeType(tree.SubstituteComment)("item", "'fake value'")
        root.nodes.append(node)

        # string
        compiled = self.compile(root, {'item': 'bound value'})
        assert compiled.sql == '?'
        assert compiled.bound_variables == ['bound value']

        # number
        compiled = self.compile(root, {'item': 20100311})
        assert compiled.sql == '?'
        assert compiled.bound_variables == [20100311]

    def test_compile_substitute_array_node(self):
        root = tree.TemplateNode(self.fname)
        node = NodeType(tree.SubstituteComment)("items", "(1)")
        root.nodes.append(node)

        # allow list
        compiled = self.compile(root, {'items': [1, 2, 3]})
        assert compiled.sql == "(?, ?, ?)"
        assert compiled.bound_variables == [1, 2, 3]

        # allow tuple
        compiled = self.compile(root, {'items': (1, 2)})
        assert compiled.sql == "(?, ?)"
        assert compiled.bound_variables == [1, 2]

        # element type is string
        compiled = self.compile(root, {'items': ['a', 'b', 'c', 'd']})
        assert compiled.sql == "(?, ?, ?, ?)"
        assert compiled.bound_variables == ['a', 'b', 'c', 'd']

    def test_compile_embed_node(self):
        root = tree.TemplateNode(self.fname)
        node = NodeType(tree.Embed)('embed', ':condition')
        root.nodes.append(node)

        compiled = self.compile(root, {'condition': """WHERE id = '1' AND status = 1"""})
        assert compiled.sql == """WHERE id = '1' AND status = 1"""
        assert compiled.bound_variables == []

    def test_compile_if_node(self):
        root = tree.TemplateNode(self.fname)
        if_node = NodeType(tree.If)('if', ':boolean_item')
        if_node.nodes.append(NodeType(tree.Literal)("""AND id = 'kjim'"""))
        root.nodes.append(if_node)

        # case: True enable if block
        compiled = self.compile(root, {'boolean_item': True})
        assert compiled.sql == """AND id = 'kjim'"""
        assert compiled.bound_variables == []

        # case: False disable if block
        compiled = self.compile(root, {'boolean_item': False})
        assert compiled.sql == ''
        assert compiled.bound_variables == []

        # case: positive number enable if block
        compiled = self.compile(root, {'boolean_item': 1})
        assert compiled.sql == """AND id = 'kjim'"""
        assert compiled.bound_variables == []

        # case: negative number enable if block
        compiled = self.compile(root, {'boolean_item': -1})
        assert compiled.sql == """AND id = 'kjim'"""
        assert compiled.bound_variables == []

        # case: number 0 disable if block
        compiled = self.compile(root, {'boolean_item': 0})
        assert compiled.sql == ''
        assert compiled.bound_variables == []

        # case: not empty str enable if block
        compiled = self.compile(root, {'boolean_item': 'some string'})
        assert compiled.sql == """AND id = 'kjim'"""
        assert compiled.bound_variables == []

        # case: empty str disable if block
        compiled = self.compile(root, {'boolean_item': ''})
        assert compiled.sql == ''
        assert compiled.bound_variables == []

    def test_compile_for_node_case_iterate_scalar_values(self):
        root = tree.TemplateNode(self.fname)
        for_node = NodeType(tree.For)('for', 'keyword in :keywords')
        for_node.nodes.append(NodeType(tree.Literal)("""AND desc LIKE '%' || """))
        for_node.nodes.append(NodeType(tree.SubstituteComment)('keyword', 'query keyword'))
        for_node.nodes.append(NodeType(tree.Literal)(""" || '%' """))
        root.nodes.append(for_node)

        compiled = self.compile(root, {'keywords': ['mc', 'mos', "denny's"]})
        assert compiled.sql == """AND desc LIKE '%' || ? || '%' """ * 3
        assert compiled.bound_variables == ['mc', 'mos', "denny's"]

    def test_compile_for_node_case_iterate_named_values(self):
        root = tree.TemplateNode(self.fname)
        for_node = NodeType(tree.For)('for', 'iteritem in :iterate_values')
        for_node.nodes.append(NodeType(tree.Literal)(""" OR """))
        for_node.nodes.append(NodeType(tree.Literal)("""("""))
        for_node.nodes.append(NodeType(tree.Literal)("""ident = """))
        for_node.nodes.append(NodeType(tree.SubstituteComment)('iteritem.ident', 9999))
        for_node.nodes.append(NodeType(tree.Literal)(""" AND """))
        for_node.nodes.append(NodeType(tree.Literal)("""password = """))
        for_node.nodes.append(NodeType(tree.SubstituteComment)('iteritem.password', 'test_pass'))
        for_node.nodes.append(NodeType(tree.Literal)(""")"""))
        root.nodes.append(for_node)

        listdata = [
            {'ident': 1105, 'password': 'kjim_pass'},
            {'ident': 3259, 'password': 'anon_pass'},
        ]
        compiled = self.compile(root, {'iterate_values': listdata})
        assert compiled.sql == """ OR (ident = ? AND password = ?)""" * 2
        assert compiled.bound_variables == [1105, 'kjim_pass', 3259, 'anon_pass']
