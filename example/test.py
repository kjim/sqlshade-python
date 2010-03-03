holder_keyword = """
select
  *
from
  t_member
where true
  and t_member.member_id = /*:member_id*/1000 -- number
  and t_member.nickname = /*:nickname*/'my nickname is holder' -- text
  and t_member.member_id in /*:member_id*/(1, 2, 3, 4, 5) -- list
  and t_member.update_ts = /*:update_ts*/CURRENT_TIMESTAMP -- literal
"""

embed_keyword = """
select
  *
from
  t_member
where true
  /*#embed :cond_keyword*/
  and (t_member.nickname like '%moonfactory%' or t_member.email like '%moonfactory%')
  /*#end*/
"""

forin_keyword_with_strlist = """
select
  *
from
  t_member
where true
  /*#for nickname in :nicknames*/
  and (t_member.nickname = /*:nickname*/'')
  and (t_member.nickname like /*:global_keyword*/'%')
  /*#end*/
"""

forin_keyword_with_maplist = """
select
  *
from
  t_member
where true
  /*#for item in :nickname_items*/
  and (t_member.firstname = /*:item.firstname*/'')
  and (t_member.lastname = /*:item.lastname*/'')
  /*#end*/
"""

enabled_keyword = """
select
  t_mycollection.mycollection_id
  , t_mycollection.member_id
  , t_mycollection.collection_title
  , (case
     when t_mycollection.update_ts is not null then t_mycollection.update_ts
     else t_mycollection.register_ts
     end
    ) as last_update_ts
  /*#enabled :join_bookmarked_self*/
  , (case
     when self_bookmarked.member_id is null then 0 -- FALSE
     else 1 -- TRUE
     end
    ) as bookmarked_self
  /*#end*/
from
  t_mycollection
  /*#enabled :join_bookmarked_self*/
  left outer join (
     select distinct
        t_mycollection_bookmark.member_id
        , t_mycollection_bookmark.reference_mycollection_id
    from
        t_mycollection_bookmark
        inner join t_member
          on (t_member.member_id = t_mycollection_bookmark.member_id)
    where true
        and t_member.member_id = /*:member_id*/10
  ) as self_bookmarked
    on (self_bookmarked.reference_mycollection_id = t_mycollection.mycollection_id)
  /*#end*/
where
  true
  and (t_mycollection.mycollection_id in /*:mycollection_ids*/(2, 3, 4))
  and (t_mycollection.status = /*:status_public*/1)
;
"""
