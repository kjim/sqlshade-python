import unittest
import copy
from datetime import datetime

from sqlshade import exc
from sqlshade.template import Template

class SubstituteAnyCaseTest(unittest.TestCase):

    def test_simple_substitute(self):
        plain_query = """SELECT * FROM t_member WHERE name = /*:nickname*/'kjim'"""
        parameters = dict(nickname='keiji')
        template = Template(plain_query, parameter_format=list)
        query, bound_variables = template.render(**parameters)
        assert query == "SELECT * FROM t_member WHERE name = ?"
        assert bound_variables == ['keiji']

        template = Template(plain_query, parameter_format=dict)
        query, bound_variables = template.render(**parameters)
        assert query == "SELECT * FROM t_member WHERE name = :nickname"
        assert bound_variables == parameters

    def test_substitute_scalar_variables(self):
        plain_query = """SELECT * FROM t_member
            WHERE TRUE
                AND t_member.age = /*:age*/1000
                AND t_member.nickname = /*:nickname*/'my nickname is holder'
                AND t_member.updated_at = /*:updated_at*/CURRENT_TIMESTAMP
                AND t_member.created_at <= /*:created_at*/now()
            ;
        """
        created_at, updated_at = datetime.now(), datetime.now()
        parameters = dict(age=25, nickname='kjim', updated_at=updated_at, created_at=created_at)

        # format: list
        template = Template(plain_query, parameter_format=list)
        query, bound_variables = template.render(**parameters)
        assert query == """SELECT * FROM t_member
            WHERE TRUE
                AND t_member.age = ?
                AND t_member.nickname = ?
                AND t_member.updated_at = ?
                AND t_member.created_at <= ?
            ;
        """
        assert bound_variables == [25, 'kjim', updated_at, created_at]

        # format: dict
        template = Template(plain_query, parameter_format=dict)
        query, bound_variables = template.render(**parameters)
        assert query == """SELECT * FROM t_member
            WHERE TRUE
                AND t_member.age = :age
                AND t_member.nickname = :nickname
                AND t_member.updated_at = :updated_at
                AND t_member.created_at <= :created_at
            ;
        """
        assert bound_variables == parameters

    def test_substitute_container_variables(self):
        plain_query = """SELECT * FROM t_member
            WHERE TRUE
                AND t_member.member_id IN /*:member_id*/(100, 200)
                AND t_member.nickname LIKE /*:nickname*/'%kjim%'
                AND t_member.sex IN /*:sex*/('male', 'female')
        """
        parameters = dict(member_id=[3845, 295, 1, 637, 221, 357], nickname='%keiji%', sex=('male', 'female', 'other'))

        # format: list
        template = Template(plain_query, parameter_format=list)
        query, bound_variables = template.render(**parameters)
        assert query == """SELECT * FROM t_member
            WHERE TRUE
                AND t_member.member_id IN (?, ?, ?, ?, ?, ?)
                AND t_member.nickname LIKE ?
                AND t_member.sex IN (?, ?, ?)
        """
        assert bound_variables == [3845, 295, 1, 637, 221, 357, '%keiji%', 'male', 'female', 'other']

        # format: dict
        template = Template(plain_query, parameter_format=dict)
        query, bound_variables = template.render(**parameters)
        assert query == """SELECT * FROM t_member
            WHERE TRUE
                AND t_member.member_id IN (:member_id_1, :member_id_2, :member_id_3, :member_id_4, :member_id_5, :member_id_6)
                AND t_member.nickname LIKE :nickname
                AND t_member.sex IN (:sex_1, :sex_2, :sex_3)
        """
        assert bound_variables == dict(
            member_id_1=3845, member_id_2=295, member_id_3=1, member_id_4=637, member_id_5=221, member_id_6=357,
            nickname='%keiji%',
            sex_1='male', sex_2='female', sex_3='other'
            )

    def test_substitute_same_keys(self):
        plain_query = """SELECT *
            FROM
                t_member
                INNER JOIN t_member_activation
                  ON (t_member_activation.member_id = t_member.member_id)
            WHERE TRUE
                AND t_member.satus = /*:status_activated*/0
                AND t_member_activation.status = /*:status_activated*/0
            ;
        """
        parameters = dict(status_activated=1)

        # format: list
        template = Template(plain_query, parameter_format=list)
        query, bound_variables = template.render(**parameters)
        assert query == """SELECT *
            FROM
                t_member
                INNER JOIN t_member_activation
                  ON (t_member_activation.member_id = t_member.member_id)
            WHERE TRUE
                AND t_member.satus = ?
                AND t_member_activation.status = ?
            ;
        """
        assert bound_variables == [1, 1]

        # format: dict
        template = Template(plain_query, parameter_format=dict)
        query, bound_variables = template.render(**parameters)
        assert query == """SELECT *
            FROM
                t_member
                INNER JOIN t_member_activation
                  ON (t_member_activation.member_id = t_member.member_id)
            WHERE TRUE
                AND t_member.satus = :status_activated
                AND t_member_activation.status = :status_activated
            ;
        """
        assert bound_variables == parameters

    def test_raise_if_has_nofeed_substitute_variables(self):
        template = Template("""SELECT * FROM t_member
            WHERE TRUE
                AND t_member.member_id IN /*:member_ids*/(100, 200, 300, 400)
                AND t_member.nickname = /*:nickname*/'kjim'
        """, parameter_format=list)
        self.assertRaises(exc.RenderError, template.render)
        self.assertRaises(exc.RenderError, template.render, nickname='keiji')

    def test_raise_if_feed_empty_substittue_list_variables(self):
        template = Template("""SELECT * FROM t_member
            WHERE TRUE
                AND t_member.member_id IN /*:member_ids*/(100, 200, 300, 400)
        """, parameter_format=list)
        self.assertRaises(exc.RenderError, template.render, member_ids=[])

class EmbedAnyCaseTest(unittest.TestCase):

    def test_usage_embed(self):
        plain_query = "SELECT * FROM /*#embed table_name*/t_aggregation_AA/*#/embed*/"
        parameters = dict(table_name='t_aggregation_AB')

        # format: list
        template = Template(plain_query, parameter_format=list)
        query, bound_variables = template.render(**parameters)
        assert query == "SELECT * FROM t_aggregation_AB"
        assert bound_variables == []

        (query, _) = template.render(table_name='t_aggregation_CB')
        assert query == "SELECT * FROM t_aggregation_CB"

        # format: dict
        template = Template(plain_query, parameter_format=dict)
        query, bound_variables = template.render(**parameters)
        assert query == "SELECT * FROM t_aggregation_AB"
        assert bound_variables == {}

    def test_no_variable_feeded(self):
        template = Template("SELECT * FROM /*#embed table_name*/t_aggregation_AA/*#/embed*/")
        self.assertRaises(exc.RenderError, template.render)

    def test_using_embed_and_substitute(self):
        plain_query = """SELECT * FROM t_member
            WHERE TRUE
                AND t_member.member_id IN /*:member_ids*/(1, 2, 3, 4, 5)
                /*#embed condition_on_runtime*/
                AND (t_member.nickname LIKE '%kjim%' or t_member.email LIKE '%linux%')
                /*#endembed*/
            ;
        """
        parameters = dict(member_ids=[23, 535, 2],
                          condition_on_runtime="AND t_member.nickname ILIKE 'linus'")

        # format: list
        template = Template(plain_query, parameter_format=list)
        (query, bound_variables) = template.render(**parameters)
        assert query == """SELECT * FROM t_member
            WHERE TRUE
                AND t_member.member_id IN (?, ?, ?)
                AND t_member.nickname ILIKE 'linus'
            ;
        """
        assert bound_variables == parameters['member_ids']

        # format: dict
        template = Template(plain_query, parameter_format=dict)
        (query, bound_variables) = template.render(**parameters)
        assert query == """SELECT * FROM t_member
            WHERE TRUE
                AND t_member.member_id IN (:member_ids_1, :member_ids_2, :member_ids_3)
                AND t_member.nickname ILIKE 'linus'
            ;
        """
        assert bound_variables == {'member_ids_1': 23, 'member_ids_2': 535, 'member_ids_3': 2}

class ForAnyCaseTest(unittest.TestCase):

    def test_usage_for(self):
        plain_query = """SELECT * FROM t_member
            WHERE TRUE
                /*#for nickname in nicknames*/
                AND (t_member.nickname = /*:nickname*/'')
                AND (t_member.nickname LIKE /*:nickname_global_cond*/'%')
                /*#endfor*/
            ;
        """
        parameters = dict(nicknames=['kjim', 'keiji'], nickname_global_cond='openbooth')

        # format: list
        template = Template(plain_query, parameter_format=list)
        query, bound_variables = template.render(**parameters)
        assert query == """SELECT * FROM t_member
            WHERE TRUE
                
                AND (t_member.nickname = ?)
                AND (t_member.nickname LIKE ?)
                
                AND (t_member.nickname = ?)
                AND (t_member.nickname LIKE ?)
                
            ;
        """
        assert bound_variables == ['kjim', 'openbooth', 'keiji', 'openbooth']

        # format: dict
        template = Template(plain_query, parameter_format=dict)
        query, bound_variables = template.render(**parameters)
        print query
        assert query == """SELECT * FROM t_member
            WHERE TRUE
                
                AND (t_member.nickname = :nickname_1)
                AND (t_member.nickname LIKE :nickname_global_cond)
                
                AND (t_member.nickname = :nickname_2)
                AND (t_member.nickname LIKE :nickname_global_cond)
                
            ;
        """
        assert bound_variables == dict(nickname_1='kjim', nickname_2='keiji', nickname_global_cond='openbooth')

    def test_using_named_value(self):
        plain_query = """SELECT * FROM t_member
            WHERE TRUE
                /*#for item in nickname_items*/
                AND (t_member.firstname = /*:item.firstname*/'keiji')
                AND (t_member.lastname = /*:item.lastname*/'muraishi')
                /*#endfor*/
            ;
        """
        parameters = dict(nickname_items=[
            dict(firstname='keiji', lastname='muraishi'),
            dict(firstname='x60', lastname='thinkpad'),
        ])

        # format: list
        template = Template(plain_query, parameter_format=list)
        query, bound_variables = template.render(**parameters)
        assert query == """SELECT * FROM t_member
            WHERE TRUE
                
                AND (t_member.firstname = ?)
                AND (t_member.lastname = ?)
                
                AND (t_member.firstname = ?)
                AND (t_member.lastname = ?)
                
            ;
        """
        assert bound_variables == ['keiji', 'muraishi', 'x60', 'thinkpad']

        # format: dict
        template = Template(plain_query, parameter_format=dict)
        query, bound_variables = template.render(**parameters)
        assert query == """SELECT * FROM t_member
            WHERE TRUE
                
                AND (t_member.firstname = :item__dot__firstname_1)
                AND (t_member.lastname = :item__dot__lastname_1)
                
                AND (t_member.firstname = :item__dot__firstname_2)
                AND (t_member.lastname = :item__dot__lastname_2)
                
            ;
        """
        assert bound_variables == {
            'item__dot__firstname_1': 'keiji', 'item__dot__lastname_1': 'muraishi',
            'item__dot__firstname_2': 'x60', 'item__dot__lastname_2': 'thinkpad',
        }

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
            /*#if join_self_favorite_data*/
            , (CASE
               WHEN self_bookmarked.owned_userid IS NULL THEN 0 -- FALSE
               ELSE 1 -- TRUE
               END
               ) AS self_favorite_data
            /*#endif*/
        FROM
            t_favorite
            /*#if join_self_favorite_data*/
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
        parameters = dict(
            join_self_favorite_data=False,
            favorite_ids=[1, 3245, 3857],
            status_activated=1
        )

        # format: list
        query, bound_variables = Template(self.query, parameter_format=list).render(**parameters)
        assert 'AS self_favorite_data' not in query
        assert 'LEFT OUTER JOIN' not in query
        assert bound_variables == [1, 3245, 3857, 1]

        # format: dict
        query, bound_variables = Template(self.query, parameter_format=dict).render(**parameters)
        assert 'AS self_favorite_data' not in query
        assert 'LEFT OUTER JOIN' not in query

        expected_parameters = dict(
            favorite_ids_1=1,
            favorite_ids_2=3245,
            favorite_ids_3=3857,
            status_activated=1)
        assert bound_variables == expected_parameters

    def test_enable_column(self):
        parameters = dict(
            join_self_favorite_data=True,
            self_userid=3586,
            favorite_ids=[11, 3245, 3857],
            status_activated=1
        )

        # format: list
        query, bound_variables = Template(self.query, parameter_format=list).render(**parameters)
        assert 'AS self_favorite_data' in query
        assert 'LEFT OUTER JOIN' in query
        assert bound_variables == [3586, 1, 11, 3245, 3857, 1]

        # format: dict
        query, bound_variables = Template(self.query, parameter_format=dict).render(**parameters)
        assert 'AS self_favorite_data' in query
        assert 'LEFT OUTER JOIN' in query

        expected_parameters = dict(
            self_userid=3586,
            favorite_ids_1=11,
            favorite_ids_2=3245,
            favorite_ids_3=3857,
            status_activated=1)
        assert bound_variables == expected_parameters

class UseCase_ReUseableWhereClause(unittest.TestCase):

    template_where_clause = Template("""
        /*#tip*/
        SELECT * FROM t_favorite WHERE TRUE
        /*#endtip*/
            /*#if use_condition_keyword*/
            AND (FALSE
                /*#for keyword in keywords*/
                OR UPPER(t_favorite.remarks) LIKE UPPER('%' || /*:keyword*/'' || '%')
                /*#endfor*/
            )
            /*#endif*/
            /*#if use_condition_fetch_status*/
            AND t_favorite.status IN /*:fetch_status*/(1, 100)
            /*#endif*/
            /*#if use_condition_sector*/
            AND t_favorite.record_type EXISTS (
                SELECT 1 FROM /*#embed sector_table*/t_sector_AA/*#endembed*/
            )
            /*#endif*/
            AND t_favorite.status = /*:status_activated*/1
        /*#tip*/
        ;
        /*#endtip*/
    """)

    def test_select_count_query(self):
        count_query = """
            SELECT COUNT(t_favorite.id) FROM t_favorite WHERE TRUE
            /*#embed where_clause*/AND TRUE/*#endembed*/
        """
        parameters = dict(
            where_clause=self.template_where_clause,
            use_condition_keyword=False,
            use_condition_fetch_status=False,
            use_condition_sector=False,
            status_activated=1
        )

        template = Template(count_query, parameter_format=list)
        query, bound_variables = template.render(**parameters)
        assert 'SELECT COUNT(t_favorite.id) FROM t_favorite WHERE TRUE' in query
        assert 'AND t_favorite.status = ?' in query
        assert bound_variables == [1]

        template = Template(count_query, parameter_format=dict)
        query, bound_variables = template.render(**parameters)
        assert 'SELECT COUNT(t_favorite.id) FROM t_favorite WHERE TRUE' in query
        assert 'AND t_favorite.status = :status_activated' in query
        assert bound_variables == dict(status_activated=parameters['status_activated'])

    def test_select_dararows(self):
        select_query = """SELECT * FROM t_favorite
            WHERE TRUE
                /*#embed where_clause*/AND TRUE/*#endembed*/
            ;
        """
        parameters = dict(
            where_clause=self.template_where_clause,
            use_condition_keyword=True, keywords=['abc', 'def', 'hij'],
            use_condition_fetch_status=False,
            use_condition_sector=True, sector_table='t_sector_ZZ',
            status_activated=1
        )

        template = Template(select_query, parameter_format=list)
        query, bound_variables = template.render(**parameters)
        assert query.count("OR UPPER(t_favorite.remarks) LIKE UPPER('%' || ? || '%')") == 3
        assert """AND t_favorite.record_type EXISTS (
                SELECT 1 FROM t_sector_ZZ
            )""" in query
        assert bound_variables == ['abc', 'def', 'hij', 1]

        template = Template(select_query, parameter_format=dict)
        query, bound_variables = template.render(**parameters)
        assert "OR UPPER(t_favorite.remarks) LIKE UPPER('%' || :keyword_1 || '%')" in query
        assert "OR UPPER(t_favorite.remarks) LIKE UPPER('%' || :keyword_2 || '%')" in query
        assert "OR UPPER(t_favorite.remarks) LIKE UPPER('%' || :keyword_3 || '%')" in query
        assert """AND t_favorite.record_type EXISTS (
                SELECT 1 FROM t_sector_ZZ
            )""" in query
        assert bound_variables == dict(keyword_1='abc', keyword_2='def', keyword_3='hij', status_activated=1)
