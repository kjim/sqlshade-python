import unittest

from sqlshade import sqlgen, tree

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

    def compile(self, node, data=None, **kwargs):
        return sqlgen.compile(node, self.fname, data or {}, **kwargs)

    def test_compile_literal_node(self):
        root = tree.TemplateNode(self.fname)
        root.nodes.append(NodeType(tree.Literal)('SELECT * FROM t_member;'))
        query, bound_variables = self.compile(root)
        assert query == 'SELECT * FROM t_member;'
        assert bound_variables == []

    def test_compile_substitute_scalar_node(self):
        root = tree.TemplateNode(self.fname)
        node = NodeType(tree.SubstituteComment)("item", "'fake value'")
        root.nodes.append(node)

        # string
        query, bound_variables = self.compile(root, {'item': 'bound value'})
        assert query == '?'
        assert bound_variables == ['bound value']

        query, bound_variables = self.compile(root, {'item': 'bound value'}, format='named_variable')
        assert query == ':item'
        assert bound_variables == {'item': 'bound value'}

        # number
        query, bound_variables = self.compile(root, {'item': 20100311})
        assert query == '?'
        assert bound_variables == [20100311]

        query, bound_variables = self.compile(root, {'item': 20100311}, format='named_variable')
        assert query == ':item'
        assert bound_variables == {'item': 20100311}

    def test_compile_substitute_array_node(self):
        root = tree.TemplateNode(self.fname)
        node = NodeType(tree.SubstituteComment)("items", "(1)")
        root.nodes.append(node)

        # allow list
        query, bound_variables = self.compile(root, {'items': [1, 2, 3]})
        assert query == "(?, ?, ?)"
        assert bound_variables == [1, 2, 3]

        query, bound_variables = self.compile(root, {'items': [1, 2, 3]}, format='named_variable')
        assert query == ":items"
        assert bound_variables == {'items': [1, 2, 3]}

        # allow tuple
        query, bound_variables = self.compile(root, {'items': (1, 2)})
        assert query == "(?, ?)"
        assert bound_variables == [1, 2]

        query, bound_variables = self.compile(root, {'items': (1, 2)}, format='named_variable')
        assert query == ":items"
        assert bound_variables == {'items': (1, 2)}

        # element type is string
        query, bound_variables = self.compile(root, {'items': ['a', 'b', 'c', 'd']})
        assert query == "(?, ?, ?, ?)"
        assert bound_variables == ['a', 'b', 'c', 'd']

        query, bound_variables = self.compile(root, {'items': ['a', 'b', 'c', 'd']}, format='named_variable')
        assert query == ":items"
        assert bound_variables == {'items': ['a', 'b', 'c', 'd']}

    def test_compile_embed_node(self):
        root = tree.TemplateNode(self.fname)
        node = NodeType(tree.Embed)('embed', ':condition')
        root.nodes.append(node)

        context = {'condition': """WHERE id = '1' AND status = 1"""}
        query, bound_variables = self.compile(root, context)
        assert query == """WHERE id = '1' AND status = 1"""
        assert bound_variables == []

        query, bound_variables = self.compile(root, context, format='named_variable')
        assert query == """WHERE id = '1' AND status = 1"""
        assert bound_variables == {}

    def test_compile_eval_node(self):
        root = tree.TemplateNode(self.fname)
        node = NodeType(tree.Eval)('eval', ':condition_template')
        root.nodes.append(node)

        query, bound_variables = self.compile(root, {'id': 98765,'condition_template': """WHERE id = /*:id*/12345"""})
        assert query == """WHERE id = ?"""
        assert bound_variables == [98765]

        query, bound_variables = self.compile(root, {'id': 98765,'condition_template': """WHERE id = /*:id*/12345"""}, format='named_variable')
        assert query == """WHERE id = :id"""
        assert bound_variables == {'id': 98765}

    def test_compile_if_node(self):
        root = tree.TemplateNode(self.fname)
        if_node = NodeType(tree.If)('if', ':boolean_item')
        if_node.nodes.append(NodeType(tree.Literal)("""AND id = 'kjim'"""))
        root.nodes.append(if_node)

        # case: True enable if block
        query, bound_variables = self.compile(root, {'boolean_item': True})
        assert query == """AND id = 'kjim'"""
        assert bound_variables == []

        query, bound_variables = self.compile(root, {'boolean_item': True}, format='named_variable')
        assert query == """AND id = 'kjim'"""
        assert bound_variables == {}

        # case: False disable if block
        query, bound_variables = self.compile(root, {'boolean_item': False})
        assert query == ''
        assert bound_variables == []

        query, bound_variables = self.compile(root, {'boolean_item': False}, format='named_variable')
        assert query == ''
        assert bound_variables == {}

        # case: positive number enable if block
        query, bound_variables = self.compile(root, {'boolean_item': 1})
        assert query == """AND id = 'kjim'"""
        assert bound_variables == []

        # case: negative number enable if block
        query, bound_variables = self.compile(root, {'boolean_item': -1})
        assert query == """AND id = 'kjim'"""
        assert bound_variables == []

        # case: number 0 disable if block
        query, bound_variables = self.compile(root, {'boolean_item': 0})
        assert query == ''
        assert bound_variables == []

        # case: not empty str enable if block
        query, bound_variables = self.compile(root, {'boolean_item': 'some string'})
        assert query == """AND id = 'kjim'"""
        assert bound_variables == []

        # case: empty str disable if block
        query, bound_variables = self.compile(root, {'boolean_item': ''})
        assert query == ''
        assert bound_variables == []

    def test_compile_for_node_case_iterate_scalar_values(self):
        root = tree.TemplateNode(self.fname)
        for_node = NodeType(tree.For)('for', 'keyword in :keywords')
        for_node.nodes.append(NodeType(tree.Literal)("""AND desc LIKE '%' || """))
        for_node.nodes.append(NodeType(tree.SubstituteComment)('keyword', 'query keyword'))
        for_node.nodes.append(NodeType(tree.Literal)(""" || '%' """))
        root.nodes.append(for_node)

        context = {'keywords': ['mc', 'mos', "denny's"]}
        query, bound_variables = self.compile(root, context)
        assert query == """AND desc LIKE '%' || ? || '%' """ * 3
        assert bound_variables == ['mc', 'mos', "denny's"]

        query, bound_variables = self.compile(root, context, format='named_variable')
        assert """AND desc LIKE '%' || :keyword_1 || '%' """ in query
        assert """AND desc LIKE '%' || :keyword_2 || '%' """ in query
        assert """AND desc LIKE '%' || :keyword_3 || '%' """ in query
        assert bound_variables == {'keyword_1': 'mc', 'keyword_2': 'mos', 'keyword_3': "denny's"}

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
        query, bound_variables = self.compile(root, {'iterate_values': listdata})
        assert query == """ OR (ident = ? AND password = ?)""" * 2
        assert bound_variables == [1105, 'kjim_pass', 3259, 'anon_pass']

    def test_resolve_context_value(self):
        resolve = sqlgen._resolve_value_in_context_data

        simple_context_data = {
            'keyword': 'keyword value',
            'password': 'Hi83i92u'
        }
        assert resolve('keyword', simple_context_data) == 'keyword value'
        assert resolve('password', simple_context_data) == 'Hi83i92u'

        nested_context_data = {
            'environ': {
                'distribution': 'ubuntu 8.10',
                'os': 'Linux',
                'kernel': '2.6.27-17-generic',
            }
        }
        assert isinstance(resolve('environ', nested_context_data), dict)
        assert resolve('environ.distribution', nested_context_data) == 'ubuntu 8.10'
        assert resolve('environ.os', nested_context_data) == 'Linux'
        assert resolve('environ.kernel', nested_context_data) == '2.6.27-17-generic'
        self.assertRaises(KeyError, resolve, *['environ.notfound', nested_context_data])
        self.assertRaises(KeyError, resolve, *['environ.', nested_context_data])

        complex_context_data = {
            'top': {
                'second': {
                    'third': {
                        'data': 'complex structure data'
                    }
                }
            }
        }
        assert resolve('top.second.third.data', complex_context_data) == 'complex structure data'
