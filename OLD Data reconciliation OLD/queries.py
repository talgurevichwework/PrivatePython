# ========================================================================================transaction-sf Queries=======================================================================================================

# Gets reuse logic records over given time period in data_trunc format
def create_sapi_reuserecords_query_notrunc(start_date, end_date):
	return(f'''
		select *
		from sales_api_public.opportunity_reuse_records as opr
		where opr.created_at >= TIMESTAMP '{start_date}' and opr.created_at < TIMESTAMP '{end_date}'
	''')

# sf closed lost query with date in normal format
def create_salesforce_closedlost_query_notrunc(start_date, end_date):
	return(f'''
		select accounts.uuid_c as account_uuid_c,
		accounts.name,
		l.country_code,
		opportunities.name as opp_name,
		case
			when (((opportunities.type_c='Hot Desk' and opportunities.type_c is not null) or (opportunities.segment_c='Enterprise Solutions'
				and opportunities.other_lost_reason_c='Hot Desk Contract Canceled New Opportunity' and opportunities.other_lost_reason_c is not null))
			and ((l.country_code<>'CHN' and l.country_code<>'ARG' and l.country_code<>'COL'
				and l.country_code<>'PER' and l.country_code<>'IND' and l.country_code<>'RUS' and l.country_code<>'CHL' and l.country_code<>'KOR') or l.country_code is null))
			then opportunities.reservation_uuid_c
			else opportunities.contract_uuid_c
		end as contract_uuid_c,
		sum(opportunities.total_desks_reserved_net_c) as net_desks_closedlost
		from salesforce_v2.opportunity as opportunities
		left join spaceman_public.locations l on l.uuid=opportunities.building_uuid_c
		left join (select uuid_c, id, name from salesforce_v2.account group by name, uuid_c, id) as accounts on opportunities.account_id=accounts.id
		where stage_name='Closed Lost' and opportunities.close_date >= TIMESTAMP '{start_date}' and opportunities.close_date < TIMESTAMP '{end_date}' and opportunities.total_desks_reserved_net_c < 0
		group by accounts.uuid_c, opportunities.contract_uuid_c, opportunities.type_c, reservation_uuid_c, opportunities.portfolio_name_c, opportunities.region_name_c, l.country_code, accounts.name,
		opportunities.other_lost_reason_c, opportunities.segment_c, opportunities.name
		''')

# sf closed won query with date in normal format
def create_salesforce_closedwon_query_notrunc(start_date, end_date):
	return(f'''
		select accounts.uuid_c as account_uuid_c,
		accounts.name,
		l.country_code,
		opportunities.name as opp_name,
		case
			when (opportunities.type_c='Hot Desk' and opportunities.type_c is not null and ((l.country_code<>'CHN' and l.country_code<>'ARG' and l.country_code<>'COL'
				and l.country_code<>'PER' and l.country_code<>'IND' and l.country_code<>'RUS' and l.country_code<>'CHL' and l.country_code<>'KOR') or l.country_code is null))
			then opportunities.reservation_uuid_c
			else opportunities.contract_uuid_c
		end as contract_uuid_c,
		sum(opportunities.no_of_desks_unweighted_c) as net_desks_closedwon
		from salesforce_v2.opportunity as opportunities
		left join spaceman_public.locations l on l.uuid=opportunities.building_uuid_c
		left join (select uuid_c, id, name from salesforce_v2.account group by name, uuid_c, id) as accounts on opportunities.account_id=accounts.id
		where stage_name='Closed Won' and opportunities.close_date >= TIMESTAMP '{start_date}' and opportunities.close_date < TIMESTAMP '{end_date}' and (lower(opportunities.contract_type_c) not like '%downgrade%' or opportunities.contract_type_c is null)
		group by accounts.uuid_c, opportunities.contract_uuid_c, opportunities.type_c, reservation_uuid_c, opportunities.portfolio_name_c, opportunities.region_name_c,
		l.country_code, accounts.name, opportunities.name
		''')

# Gets v_transaction records over given time period in normal date format as well as contract uuid from corresponding membership agreement
def create_vtrans_query_notrunc(start_date, end_date):
	return(f'''
with vtrans as (select v.account_name,
		v.account_uuid,
		l.country_code,
		sum(v.desks_changed) as desks_changed,
			case
				when (v.reservable_type='HotDesk' and l.country_code<>'CHN' and l.country_code<>'ARG' and l.country_code<>'COL'
				and l.country_code<>'PER' and l.country_code<>'IND' and l.country_code<>'RUS' and l.country_code<>'CHL' and l.country_code<>'KOR')
			then v.reservation_uuid
			else ma.uuid
			end as contract_uuid
		from dw.v_transaction v
	left join spaceman_public.locations l on l.uuid=v.location_uuid
	left join (select r.uuid, r.id from spaceman_public.reservations r group by r.uuid, r.id) r on r.uuid=v.reservation_uuid
	left join (select cr.reservation_id, cr.membership_agreement_id, cr.reservation_started_on, cr.reservation_ended_on from spaceman_public.change_requests cr
		where cr.executed_at >= DATEADD(day , -1 , '2018-06-01') and cr.executed_at < DATEADD(day, 1, '2018-07-01')
		group by cr.reservation_id, cr.membership_agreement_id, cr.reservation_started_on, cr.reservation_ended_on) cr on cr.reservation_id=r.id
			and (((v.action_type='Transfer In' or v.action_type='Move In') and cr.reservation_started_on is not null) or
			(v.action_type='Transfer Out' or v.action_type='Move Out') and cr.reservation_ended_on is not null)
	left join (select ma.id, ma.uuid from spaceman_public.membership_agreements ma group by ma.id, ma.uuid) ma on ma.id=cr.membership_agreement_id
		where date_reserved_local >=TIMESTAMP '{start_date}' and date_reserved_local <TIMESTAMP '{end_date}'
		group by v.account_name, v.account_uuid, v.reservable_type, v.city, v.reservation_uuid, ma.uuid, l.country_code)
			select account_name, account_uuid, country_code, sum(desks_changed) as desks_changed, contract_uuid
				from vtrans
				group by account_name, account_uuid, contract_uuid, country_code
		''')

# ========================================================================================label_sync_issues Queries=======================================================================================================

# Returns date frame with opportunities connected to given reservation uuid
def create_hd_opp_query(reservation_uuid, move_type):
	stage = 'Closed Lost' if move_type == 'moveout' else 'Closed Won'
	return(f'''
			select o.reservation_uuid_c, o.name, o.region_name_c, o.territory_name_c, o.building_city_c, o.no_of_desks_unweighted_c, o.total_desks_reserved_net_c, o.close_date, o.stage_name
			from salesforce_v2.opportunity o
			where o.reservation_uuid_c='{reservation_uuid}' and o.stage_name='{stage}'
		''')

# Returns date frame with reservations connected to given reservation uuid
def create_hd_res_query(reservation_uuid):
	return(f'''
			select * from dw.v_transaction v where v.reservation_uuid='{reservation_uuid}'
		''')

# ========================================================================================looker-sf Queries=======================================================================================================

# sf closed lost query with date in data_trunc (i.e Looker) format (combine with sf closed won query to create sfdc report)
def create_salesforce_closedlost_query(time_period, start_date, end_date):
	return(f'''
		select accounts.uuid_c as account_uuid_c, sum(opportunities.total_desks_reserved_net_c) as net_desks_closedlost, date_trunc (lower('{time_period}'), opportunities.close_date)::date as date
		from salesforce_v2.opportunity as opportunities
		left join (select uuid_c, id from salesforce_v2.account group by uuid_c, id) as accounts on opportunities.account_id=accounts.id
		where stage_name='Closed Lost' and date_trunc (lower('{time_period}'), opportunities.close_date)::date>=TIMESTAMP '{start_date}' and date_trunc (lower('{time_period}'), opportunities.close_date)::date<TIMESTAMP '{end_date}' and opportunities.total_desks_reserved_net_c<0 and opportunities.region_name_c<>'India'
		group by accounts.uuid_c, date_trunc (lower('{time_period}'), opportunities.close_date)
		''')

# sf closed won query with date in data_trunc (i.e Looker) format (combine with sf closed lost query to create sfdc report)
def create_salesforce_closedwon_query(time_period, start_date, end_date):
	return(f'''
		select accounts.uuid_c as account_uuid_c, sum(opportunities.no_of_desks_unweighted_c) as net_desks_closedwon, date_trunc (lower('{time_period}'), opportunities.close_date)::date as date
		from salesforce_v2.opportunity as opportunities
		left join (select uuid_c, id from salesforce_v2.account group by uuid_c, id) as accounts on opportunities.account_id=accounts.id
		where stage_name='Closed Won' and date_trunc (lower('{time_period}'), opportunities.close_date)::date>=TIMESTAMP '{start_date}' and date_trunc (lower('{time_period}'), opportunities.close_date)::date<TIMESTAMP '{end_date}' and (lower(opportunities.contract_type_c) not like '%downgrade%' or opportunities.contract_type_c is null) and opportunities.region_name_c<>'India'
		group by accounts.uuid_c, date_trunc (lower('{time_period}'), opportunities.close_date)
		''')

# Gets reuse logic records over given time period in data_trunc format
def create_sapi_reuserecords_query(time_period, start_date, end_date):
	return(f'''
		select *
		from sales_api_public.opportunity_reuse_records as opr
		where date_trunc(lower('{time_period}'), opr.created_at)::date>=TIMESTAMP '{start_date}' and date_trunc (lower('{time_period}'), opr.created_at)::date<TIMESTAMP '{end_date}'
	''')

# Gets reservations, change_requests, membership_agreements over time period in data_trunc format
def create_spaceman_r_cr_ma_query(time_period, start_date, end_date):
	return(f'''
		with ma as (
			select *
			from spaceman_public.membership_agreements ma),
		r as (
			select *
			from spaceman_public.reservations r),
		cr as (
			select *
			from spaceman_public.change_requests cr)
		select cr.account_uuid as account_uuid,
			ma.created_at as ma_created,
			cr.created_at as cr_created,
			r.created_at as reservation_created,
			r.uuid as reservation_uuid,
			ma.uuid as ma_uuid,
			cr.sf_opportunity_id,
			ma.signed_at,
			cr.reservation_started_on,
			cr.reservation_ended_on,
			r.description as reservable
		from cr
		full join ma on ma.id = cr.membership_agreement_id
		full join r on r.id = cr.reservation_id
		where date_trunc(lower('{time_period}'), ma.created_at)::date>=TIMESTAMP '{start_date}' and date_trunc (lower('{time_period}'), ma.created_at)::date<TIMESTAMP '{end_date}'
		and cr.reservation_type = 'PrimaryReservation'
		''')

# Creates looker query over given time period in data_trunc format
def create_looker_query(time_period, start_date, end_date):
	return(f'''
		WITH new_sales_reporting AS (select
		        '{time_period}' as time_grouping,
		        'no' as include_jv_markets,
		        'Global' as select_grouping,
		        date_trunc (lower('{time_period}'), v.date_reserved_local)::date as date,
		      v.account_uuid,
		      v.account_name,
		      case
		        when 'Global' = 'Location'
		          then t.location_name
		        when 'Global'= 'City'
		          then t.city
		        when 'Global'= 'Market'
		          then t.sales_market
		        when 'Global'= 'Territory'
		          then t.territory
		        when 'Global'= 'Region'
		          then t.region
		        when 'Global'= 'Global'
		          then 'Global'
		        else null
		      end as user_selection,
		      case
		        when 'Global' = 'Location'
		          then t.location_name
		        else null
		      end as location_name,
		      case
		        when 'Global' = 'Location'
		          then t.location_uuid
		        else null
		      end as location_uuid,
		      case
		        when 'Global' = 'Location'
		          then t.opened_on
		        else null
		      end as opened_on,
		      case
		        when 'Global' = 'Location'
		        then datediff('month',t.opened_on,v.date_reserved_local)
		        else null
		      end as month_no,
		      case
		        when 'Global' = 'Location'
		        then t.code
		        else null
		      end as building_short_code,
		      case
		        when 'Global' = 'Location'
		          then t.city
		        when 'Global' = 'City'
		          then t.city
		        else null
		      end as city,
		      case
		        when 'Global' = 'Location'
		          then t.sales_market
		        when 'Global'= 'City'
		          then t.sales_market
		        when 'Global'= 'Market'
		          then t.sales_market
		        else null
		      end as market,
		      case
		        when 'Global' = 'Location'
		          then t.territory
		        when 'Global'= 'City'
		          then t.territory
		        when 'Global'= 'Market'
		          then t.territory
		        when 'Global'= 'Territory'
		          then t.territory
		        else null
		      end as territory,
		      case
		        when 'Global' = 'Location'
		          then t.region
		        when 'Global'= 'City'
		          then t.region
		        when 'Global'= 'Market'
		          then t.region
		        when 'Global'= 'Territory'
		          then t.region
		        when 'Global'= 'Region'
		          then t.region --xxxxxxxxxxxxxxxxxxxxxxxxxxx
		        else null
		      end as region,
		        case
		          when sum(case when transfer_type is not null then desks_changed else 0 end) >0
		        then
		          sum(case when transfer_type is not null then desks_changed else 0 end) + sum(NVL(net_zero_transfer_ins.net_zero_upgrades,0))
		        else
		          sum(NVL(net_zero_transfer_ins.net_zero_upgrades,0))
		        end as
		        upgrades,
		        case
		          when sum(case when transfer_type is not null then desks_changed else 0 end) < 0
		          then
		              sum(case when transfer_type is not null then desks_changed else 0 end) + sum(NVL(net_zero_transfer_outs.net_zero_downgrades,0))
		          else
		            sum(NVL(net_zero_transfer_outs.net_zero_downgrades,0))
		        end as
		        downgrades,
		        sum(case when action_type = 'Move In' then desks_changed else 0 end) as new_sales,
		        sum(case when action_type = 'Move Out' then desks_changed else 0 end) as churn_notice,
		        date_trunc('month',max(case when desks_changed > 0 then date_physical_move else null end)) as last_date_physical_move,
		        listagg(distinct case when action_type = 'Transfer Out' then t.location_name else null end, ', ') as transfer_out_locations,
		        listagg(distinct case when action_type = 'Transfer In' then t.location_name else null end, ', ') as transfer_in_locations,
		        row_number() over() as id
		        from dw.v_transaction v
		        left join dw.mv_dim_location t
		        on v.location_uuid = t.location_uuid
		        -- Net Zero Transfers are when a reservation is created and notice is given in the same month
		        -- These are added to the upgrade & downgrade totals, as both an upgrade and a downgrade
		        -- The reservation has to be at least 1 month
		        left join (
		                  SELECT sold_at_local,
		                  reservation_uuid,
		                  real_capacity AS net_zero_upgrades,
		                  datediff('days',date_started, date_ended)
		                  FROM dw.mv_fact_reservable_reservation r
		                  WHERE date_trunc (lower('{time_period}'),sold_at_local)::date = date_trunc (lower('{time_period}'), gave_notice_local)::date
		                  AND move_in_type ilike '%Transfer'
		                  AND move_out_type ilike '%Transfer'
		                  AND datediff('days',date_started, date_ended) >= 27
		        ) AS net_zero_transfer_ins
		          ON net_zero_transfer_ins.reservation_uuid = v.reservation_uuid
		          AND date_trunc (lower('{time_period}'), net_zero_transfer_ins.sold_at_local)::date = date_trunc (lower('{time_period}'), v.date_reserved_local)::date
		          AND v.action_type = 'Transfer In'
		        left join (
		                  SELECT gave_notice_local,
		                  reservation_uuid,
		                  real_capacity * -1 AS net_zero_downgrades,
		                  datediff('days',date_started, date_ended)
		                  FROM dw.mv_fact_reservable_reservation r
		                  WHERE date_trunc (lower('{time_period}'), sold_at_local)::date = date_trunc (lower('{time_period}'), gave_notice_local)::date
		                  AND move_in_type ilike '%Transfer'
		                  AND move_out_type ilike '%Transfer'
		                  AND datediff('days',date_started, date_ended) >= 27
		        ) AS net_zero_transfer_outs
		          ON net_zero_transfer_outs.reservation_uuid = v.reservation_uuid
		          AND date_trunc (lower('{time_period}'), net_zero_transfer_outs.gave_notice_local)::date = date_trunc (lower('{time_period}'), v.date_reserved_local)::date
		          AND v.action_type = 'Transfer Out'
		        where CASE WHEN 'no' = 'no'
		              THEN NOT t.is_joint_venture ELSE True END
		        group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16
		        order by 2
		      )
		SELECT
			new_sales_reporting.account_name  AS "new_sales_reporting.account_name",
			accounts.account_uuid  AS "accounts.account_uuid",
			new_sales_reporting.date as "close_date",
			COALESCE(SUM(new_sales_reporting.upgrades + new_sales_reporting.new_sales), 0) AS "new_sales_reporting.net_sales_1"
		FROM new_sales_reporting
		LEFT JOIN dw.mv_dim_account  AS accounts ON new_sales_reporting.account_uuid=accounts.account_uuid
		WHERE
			(((new_sales_reporting.date) >= (TIMESTAMP '{start_date}') AND (new_sales_reporting.date) < (TIMESTAMP '{end_date}')))
		GROUP BY 1,2,3
		ORDER BY 3 DESC
		''')