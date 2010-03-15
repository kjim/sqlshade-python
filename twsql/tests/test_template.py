import unittest
from datetime import datetime
from cStringIO import StringIO

from twsql import exc
from twsql.template import Template

class RenderFunctionTestCase(unittest.TestCase):

    @property
    def buf(self):
        return self._buf

    def setUp(self):
        self._buf = StringIO()

    def tearDown(self):
        self._buf.close()

class SubstituteAnyCaseTest(unittest.TestCase):

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

    def test_substitute_container_variables(self):
        template = Template("""
            SELECT
                *
            FROM
                t_member
            WHERE TRUE
                AND t_member.member_id IN /*:member_id*/(100, 200)
                AND t_member.nickname LIKE /*:nickname*/'%kjim%'
                AND t_member.sex IN /*:sex*/('male', 'female')
        """)
        query, bound_variables = template.render(
            member_id=[3845, 295, 1, 637, 221, 357],
            nickname='%keiji%',
            sex=('male', 'female', 'other')
        )
        assert query == """
            SELECT
                *
            FROM
                t_member
            WHERE TRUE
                AND t_member.member_id IN (?, ?, ?, ?, ?, ?)
                AND t_member.nickname LIKE ?
                AND t_member.sex IN (?, ?, ?)
        """
        assert bound_variables == [3845, 295, 1, 637, 221, 357, '%keiji%', 'male', 'female', 'other']

    def test_substitute_same_keys(self):
        template = Template("""
            select
                *
            from
                t_member
                inner join t_member_activation
                  on (t_member_activation.member_id = t_member.member_id)
            where true
                and t_member.satus = /*:status_activated*/0
                and t_member_activation.status = /*:status_activated*/0
        """)
        query, bound_variables = template.render(status_activated=1)
        assert query == """
            select
                *
            from
                t_member
                inner join t_member_activation
                  on (t_member_activation.member_id = t_member.member_id)
            where true
                and t_member.satus = ?
                and t_member_activation.status = ?
        """
        assert bound_variables == [1, 1]

    def test_raise_if_has_nofeed_substitute_variables(self):
        template = Template("""
            select
                *
            from
                t_member
            where true
                and t_member.member_id in /*:member_ids*/(100, 200, 300, 400)
                and t_member.nickname = /*:nickname*/'kjim'
        """)
        self.assertRaises(exc.RuntimeError, template.render)
        self.assertRaises(exc.RuntimeError, template.render, nickname='keiji')

    def test_raise_if_feed_empty_substittue_list_variables(self):
        template = Template("""
            select
                *
            from
                t_member
            where true
                and t_member.member_id in /*:member_ids*/(100, 200, 300, 400)
        """)
        self.assertRaises(exc.RuntimeError, template.render, member_ids=[])

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

class EmbedAnyCaseTest(unittest.TestCase):

    def test_usage_embed(self):
        template = Template("SELECT * FROM /*#embed :table_name*/t_aggregation_AA/*#/embed*/")
        query, bound_variables = template.render(table_name='t_aggregation_AB')
        assert query == "SELECT * FROM t_aggregation_AB"
        assert bound_variables == []

        (query, _) = template.render(table_name='t_aggregation_CB')
        assert query == "SELECT * FROM t_aggregation_CB"

    def test_no_variable_feeded(self):
        template = Template("SELECT * FROM /*#embed :table_name*/t_aggregation_AA/*#/embed*/")
        self.assertRaises(exc.RuntimeError, template.render)
