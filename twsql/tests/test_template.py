import unittest
from datetime import datetime
from cStringIO import StringIO

from twsql.template import Template

class RenderFunctionTestCase(unittest.TestCase):

    @property
    def buf(self):
        return self._buf

    def setUp(self):
        self._buf = StringIO()

    def tearDown(self):
        self._buf.close()

class TemplateUsageTest(unittest.TestCase):

    def test_simple_substitute(self):
        template = Template("""SELECT * FROM t_member WHERE name = /*:name*/'kjim'""")
        query, bound_variables = template.render(name='keiji')
        assert query == """SELECT * FROM t_member WHERE name = ?"""
        assert bound_variables == ['keiji']

    def test_substitute_scalar_variables(self):
        template = Template("""
            SELECT
                *
            FROM
                t_member
            WHERE TRUE
                AND t_member.age = /*:age*/1000
                AND t_member.nickname = /*:nickname*/'my nickname is holder'
                AND t_member.updated_at = /*:updated_at*/CURRENT_TIMESTAMP
                AND t_member.created_at <= /*:created_at*/now()
            ;
        """)
        created_at, updated_at = datetime.now(), datetime.now()
        query, bound_variables = template.render(
            age=25,
            nickname='kjim',
            updated_at=updated_at,
            created_at=created_at
        )
        assert query == """
            SELECT
                *
            FROM
                t_member
            WHERE TRUE
                AND t_member.age = ?
                AND t_member.nickname = ?
                AND t_member.updated_at = ?
                AND t_member.created_at <= ?
            ;
        """
        assert bound_variables == [25, 'kjim', updated_at, created_at]

    def test_substitute_any_case(self):
        template = Template("""
            SELECT
                t_template.id
            FROM
                t_template
            WHERE
                t_template.engine = /*:engine*/'substitute me'
                AND t_template.feature in /*:features*/('slow', 'VALIDHTML')
            ;
        """)
        query, bound_variables = template.render(engine='mako', features=['fast', 'non-XML', 'cacheable'])
        assert query == """
            SELECT
                t_template.id
            FROM
                t_template
            WHERE
                t_template.engine = ?
                AND t_template.feature in (?, ?, ?)
            ;
        """
        assert bound_variables == ['mako', 'fast', 'non-XML', 'cacheable']

    def test_dynamic_select_column_query_template(self):
        template = Template("""
            SELECT
                t_template.id
                /*#for column in :table_columns*/
                , /*#embed :column*/t_template.engine/*#endembed*/
                /*#endfor*/
            FROM
                t_template
            WHERE
                FALSE
                /*#for cond in :cond_engines*/
                OR (t_template.engine = /*:cond.engine*/'mako' AND t_template.feature IN /*:cond.features*/('fast'))
                /*#endfor*/
            ;
        """)
        query, bound_variables = template.render(
            table_columns=[
                't_template.engine',
                't_template.feature',
            ],
            cond_engines=[
                { 'engine': 'Mako', 'features': ['fast', 'non-XML', 'module'] },
                { 'engine': 'Jinja2', 'features': ['fast', 'non-XML'] },
                { 'engine': 'Genshi', 'features': ['XML'] },
            ]
        )
        assert ", t_template.engine" in query
        assert ", t_template.feature" in query
        assert "OR (t_template.engine = ? AND t_template.feature IN (?, ?, ?))" in query
        assert "OR (t_template.engine = ? AND t_template.feature IN (?, ?))" in query
        assert "OR (t_template.engine = ? AND t_template.feature IN (?))" in query
        assert bound_variables == [
            'Mako',
            'fast',
            'non-XML',
            'module',
            'Jinja2',
            'fast',
            'non-XML',
            'Genshi',
            'XML',
        ]

    def test_eval_tricks(self):
        template = Template("""
            SELECT
                *
            FROM
                t_template
            WHERE TRUE
                /*#eval :cond_trick_literal*/
                AND (t_template.engine = 'Mako')
                /*#endeval*/
            ;
        """)
        query, bound_variables = template.render(
            cond_trick_literal="""AND (t_template.engine = /*:cond_engine*/'Mako')""",
            cond_engine='Genshi'
        )
        assert query == """
            SELECT
                *
            FROM
                t_template
            WHERE TRUE
                AND (t_template.engine = ?)
            ;
        """
        assert bound_variables == ['Genshi']
