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
