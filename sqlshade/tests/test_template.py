import unittest
from datetime import datetime
from cStringIO import StringIO

from sqlshade import exc
from sqlshade.template import Template

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

    def test_using_embed_and_substitute(self):
        template = Template("""
            SELECT
                *
            FROM
                t_member
            WHERE TRUE
                AND t_member.member_id IN /*:member_ids*/(1, 2, 3, 4, 5)
                /*#embed :condition_on_runtime*/
                AND (t_member.nickname LIKE '%kjim%' or t_member.email LIKE '%linux%')
                /*#endembed*/
            ;
        """)
        (query, _) = template.render(
            member_ids=[23, 535, 2],
            condition_on_runtime="AND t_member.nickname ILIKE 'linus'"
        )
        assert query == """
            SELECT
                *
            FROM
                t_member
            WHERE TRUE
                AND t_member.member_id IN (?, ?, ?)
                AND t_member.nickname ILIKE 'linus'
            ;
        """

class ForAnyCaseTest(unittest.TestCase):

    def test_usage_for(self):
        template = Template("""
            SELECT
                *
            FROM
                t_member
            WHERE TRUE
                /*#for nickname in :nicknames*/
                AND (t_member.nickname = /*:nickname*/'')
                AND (t_member.nickname LIKE /*:nickname_global_cond*/'%')
                /*#endfor*/
            ;
        """)
        query, bound_variables = template.render(nicknames=['kjim', 'keiji'], nickname_global_cond='openbooth')
        print query
        assert query == """
            SELECT
                *
            FROM
                t_member
            WHERE TRUE
                
                AND (t_member.nickname = ?)
                AND (t_member.nickname LIKE ?)
                
                AND (t_member.nickname = ?)
                AND (t_member.nickname LIKE ?)
                
            ;
        """
        assert bound_variables == ['kjim', 'openbooth', 'keiji', 'openbooth']

    def test_using_named_value(self):
        template = Template("""
            SELECT
                *
            FROM
                t_member
            WHERE TRUE
                /*#for item in :nickname_items*/
                AND (t_member.firstname = /*:item.firstname*/'keiji')
                AND (t_member.lastname = /*:item.lastname*/'muraishi')
                /*#endfor*/
            ;
        """)
        query, bound_variables = template.render(nickname_items=[
            { 'firstname': 'keiji', 'lastname': 'muraishi' },
            { 'firstname': 'x60', 'lastname': 'thinkpad' },
        ])
        assert query == """
            SELECT
                *
            FROM
                t_member
            WHERE TRUE
                
                AND (t_member.firstname = ?)
                AND (t_member.lastname = ?)
                
                AND (t_member.firstname = ?)
                AND (t_member.lastname = ?)
                
            ;
        """
        assert bound_variables == ['keiji', 'muraishi', 'x60', 'thinkpad']

class UseCase_DynamicAppendableColumn(unittest.TestCase):

    query = """
        SELECT
            t_favorite.id
            , t_favorite.owned_userid
            , t_favorite.remarks
            , (CASE
               WHEN t_favorite.updated_at IS NOT NULL THEN t_favorite.updated_at
               ELSE t_favorite.created_at
               END
               ) AS last_updated_at
            /*#if :join_self_favorite_data*/
            , (CASE
               WHEN self_bookmarked.owned_userid IS NULL THEN 0 -- FALSE
               ELSE 1 -- TRUE
               END
               ) AS self_favorite_data
            /*#endif*/
        FROM
            t_favorite
            /*#if :join_self_favorite_data*/
            LEFT OUTER JOIN (
                SELECT DISTINCT
                    t_favorite_item.owned_userid
                    , t_favorite_item.reference_id
                FROM
                    t_favorite_item
                    INNER JOIN t_member
                      on (t_member.id = t_favorite_item.owned_userid)
                WHERE TRUE
                    AND t_member.id = /*:self_userid*/10
                    AND t_member.status = /*:status_activated*/1
            ) as self_bookmarked
                on (self_bookmarked.reference_id = t_favorite.id)
            /*#endif*/
        WHERE
            TRUE
            AND (t_favorite.id IN /*:favorite_ids*/(2, 3, 4))
            AND (t_favorite.status = /*:status_activated*/1)
        ;
    """

    def setUp(self):
        self.template = Template(self.query)

    def test_disable_column(self):
        query, bound_variables = self.template.render(
            join_self_favorite_data=False,
            favorite_ids=[1, 3245, 3857],
            status_activated=1
        )
        assert 'AS self_favorite_data' not in query
        assert 'LEFT OUTER JOIN' not in query
        assert bound_variables == [1, 3245, 3857, 1]

    def test_enable_column(self):
        query, bound_variables = self.template.render(
            join_self_favorite_data=True,
            self_userid=3586,
            favorite_ids=[11, 3245, 3857],
            status_activated=1
        )
        assert 'AS self_favorite_data' in query
        assert 'LEFT OUTER JOIN' in query
        assert bound_variables == [3586, 1, 11, 3245, 3857, 1]

class UseCase_ReUseableWhereClause(unittest.TestCase):

    exectable_where_clause_query = """
        /*#if :false*/
        SELECT * FROM t_favorite WHERE TRUE
        /*#endif*/
            /*#if :use_condition_keyword*/
            AND (FALSE
                /*#for keyword in :keywords*/
                OR UPPER(t_favorite.remarks) LIKE UPPER('%' || /*:keyword*/'' || '%')
                /*#endfor*/
            )
            /*#endif*/
            /*#if :use_condition_fetch_status*/
            AND t_favorite.status IN /*:fetch_status*/(1, 100)
            /*#endif*/
            /*#if :use_condition_sector*/
            AND t_favorite.record_type EXISTS (
                SELECT 1 FROM /*#embed :sector_table*/t_sector_AA/*#endembed*/
            )
            /*#endif*/
            AND t_favorite.status = /*:status_activated*/1
        /*#if :false*/
        ;
        /*#endif*/
    """

    def test_select_count_query(self):
        template_where_clause = Template(self.exectable_where_clause_query, strict=False)
        (tmp_query, _) = template_where_clause.render(false=False)
        assert 'SELECT * FROM t_favorite WHERE TRUE' not in tmp_query
        assert ';' not in tmp_query
        assert """
            /*#if :use_condition_keyword*/
            AND (FALSE
                /*#for keyword in :keywords*/
                OR UPPER(t_favorite.remarks) LIKE UPPER('%' || /*:keyword*/'' || '%')
                /*#endfor*/
            )
            /*#endif*/
            /*#if :use_condition_fetch_status*/
            AND t_favorite.status IN /*:fetch_status*/(1, 100)
            /*#endif*/
            /*#if :use_condition_sector*/
            AND t_favorite.record_type EXISTS (
                SELECT 1 FROM /*#embed :sector_table*/t_sector_AA/*#endembed*/
            )
            /*#endif*/
            AND t_favorite.status = /*:status_activated*/1
            """.strip() in tmp_query

        template = Template("""
            SELECT COUNT(t_favorite.id) FROM t_favorite WHERE TRUE
            /*#eval :where_clause*/AND TRUE/*#endeval*/
        """)
        query, bound_variables = template.render(
            where_clause=tmp_query,
            use_condition_keyword=False,
            use_condition_fetch_status=False,
            use_condition_sector=False,
            status_activated=1
        )
        assert 'SELECT COUNT(t_favorite.id) FROM t_favorite WHERE TRUE' in query
        assert 'AND t_favorite.status = ?' in query
        assert bound_variables == [1]

    def test_select_dararows(self):
        template_where_clause = Template(self.exectable_where_clause_query, strict=False)
        (tmp_query, _) = template_where_clause.render(false=False)

        template = Template("""
            SELECT
                *
            FROM
                t_favorite
            WHERE TRUE
                /*#eval :where_clause*/AND TRUE/*#endeval*/
            ;
        """)
        query, bound_variables = template.render(
            where_clause=tmp_query,
            use_condition_keyword=True, keywords=['abc', 'def', 'hij'],
            use_condition_fetch_status=False,
            use_condition_sector=True, sector_table='t_sector_ZZ',
            status_activated=1
        )
        assert query.count("OR UPPER(t_favorite.remarks) LIKE UPPER('%' || ? || '%')") == 3
        assert """AND t_favorite.record_type EXISTS (
                SELECT 1 FROM t_sector_ZZ
            )""" in query
        assert bound_variables == ['abc', 'def', 'hij', 1]