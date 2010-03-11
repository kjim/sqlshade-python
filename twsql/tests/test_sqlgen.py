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

    def test_compile_literal_node_only(self):
        root = tree.TemplateNode(self.fname)
        root.nodes.append(NodeType(tree.Literal)('SELECT * FROM t_member;'))
        compiled = self.compile(root)
        assert compiled.sql == 'SELECT * FROM t_member;'
        assert compiled.bound_variables == []

    def test_compile_substitute_scalar_node_only(self):
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

    def test_compile_substitute_array_node_only(self):
        # allow list
        root = tree.TemplateNode(self.fname)
        node = NodeType(tree.SubstituteComment)("items", "(1)")
        root.nodes.append(node)
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
