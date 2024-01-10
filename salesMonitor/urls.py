from django.urls import path

from salesMonitor import amazon

from . import views

urlpatterns = [
    path('update_last_year_sales', views.update_last_year_sales, name='update_last_year_sales'),
    path('update_7d_orders', views.update_7d_orders, name='update_7d_orders'),
    path('update_restock_report', views.update_restock_report, name='update_restock_report'),
    path('update_remote_fulfillment_eligible_ASIN_Report', views.update_remote_fulfillment_eligible_ASIN_Report, name='update_remote_fulfillment_eligible_ASIN_Report'),
    path('update_currency_rate', views.update_currency_rate, name='update_currency_rate'),
    path('update_shenzhen_inventory', views.update_shenzhen_inventory, name='update_shenzhen_inventory'),
    path('update_purchasing_orders', views.update_purchasing_orders, name='update_purchasing_orders'),
    path('restock_today', views.restock_today, name='restock_today'),
    path('shipment_today', views.shipment_today, name='shipment_today'),
    path('reprice_today', views.reprice_today, name='reprice_today'),
    path('update_today_sales', views.update_today_sales, name='update_today_sales'),
    path('<int:year>/<int:month>/<int:day>/', views.history_index, name='history_index'),

    path('update_fba_shipment', views.update_fba_shipment, name='update_fba_shipment'),
    path('update_fba_shipment_paid_bills', views.update_fba_shipment_paid_bills, name='update_fba_shipment_paid_bills'),
    path('export_sku_inbound_shipping_cost', views.export_sku_inbound_shipping_cost, name='export_sku_inbound_shipping_cost'),
    path('export_sku_inbound_shipping_cost_for_sellfox', views.export_sku_inbound_shipping_cost_for_sellfox, name='export_sku_inbound_shipping_cost_for_sellfox'),
    # path('update_sku_weight', views.update_sku_weight, name='update_sku_weight'),
    path('update_fba_shipment_estimated_receiving_date', views.update_fba_shipment_estimated_receiving_date, name='update_fba_shipment_estimated_receiving_date'),
    path('update_fba_shipment_received_sku_qty', views.update_fba_shipment_received_sku_qty, name='update_fba_shipment_received_sku_qty'),
    path('estimated_sku_qty_receiving_date', views.estimated_sku_qty_receiving_date, name='estimated_sku_qty_receiving_date'),
    path('get_estimated_sku_qty_receiving_date_of_a_sku', views.get_estimated_sku_qty_receiving_date_of_a_sku, name='get_estimated_sku_qty_receiving_date_of_a_sku'),
    path('', views.index, name='today_sales'),
    path('other_country_today_sales/<slug:country>/', views.other_country_today_sales, name='other_country_today_sales'),
    path('get_history_sales_of_a_sku', views.get_history_sales_of_a_sku, name='get_history_sales_of_a_sku'),
    path('get_top_sales_vialation/<slug:country>/', views.get_top_sales_vialation, name='get_top_sales_vialation'),
    path('get_excess_inventory/<slug:country>/', views.get_excess_inventory, name='get_excess_inventory'),

    path('get_reviews_stat', views.get_reviews_stat, name='get_reviews_stat'),
    path('get_upcs', views.get_upcs, name='get_upcs'),
    path('input_upcs', views.input_upcs, name='input_upcs'),
    path('update_sku_supplier', views.update_sku_supplier, name='update_sku_supplier'),

    path('product_information', views.product_information, name= 'product_information'),
    path('product_information_export', views.product_information_export, name= 'product_information_export'),
    path('update_product_information_in_bulk', views.update_product_information_in_bulk, name= 'update_product_information_in_bulk'),

    path('update_all_product_purchase_price', views.update_all_product_purchase_price,name='update_all_product_purchase_price'),
    path('update_all_product_head_shipping_unit_cost', views.update_all_product_head_shipping_unit_cost,name='update_all_product_head_shipping_unit_cost'),
    path('update_sales_person_and_managing_sku_list', views.update_sales_person_and_managing_sku_list, name='update_sales_person_and_managing_sku_list'),

    path('update_inventory_value', views.update_inventory_value,name='update_inventory_value'),
    path('update_inventory_additional_value', views.update_inventory_additional_value,name='update_inventory_additional_value'),
    path('update_paid_purchase_order', views.update_paid_purchase_order,name='update_paid_purchase_order'),
    path('update_sales_transaction', views.update_sales_transaction,name='update_sales_transaction'),
    path('confirm_po_head_shipping', views.confirm_po_head_shipping,name='confirm_po_head_shipping'),

    path('get_sku_pl_al_table/<slug:sku>/', views.get_sku_pl_al_table,name='get_sku_pl_al_table'),

    path('finance_dashboard', views.finance_dashboard,name='finance_dashboard'),

    path('get_ongoing_production_plan_progresses', views.get_ongoing_production_plan_progresses, name='get_ongoing_production_plan_progresses'),
    path('get_ongoing_production_plan_progresses_by_sku', views.get_ongoing_production_plan_progresses_by_sku, name='get_ongoing_production_plan_progresses_by_sku'),
    path('production_plan_today', views.production_plan_today, name='production_plan_today'),
    path('update_purchasing_orders_including_completed', views.update_purchasing_orders_including_completed, name='update_purchasing_orders_including_completed'),
    path('update_sku_production_stage_by_a_reference', views.update_sku_production_stage_by_a_reference, name='update_sku_production_stage_by_a_reference'),
    path('update_sku_production_stage_detailed_numbers_default', views.update_sku_production_stage_detailed_numbers_default, name='update_sku_production_stage_detailed_numbers_default'),
    path('update_ongoing_production_plan_progress/<slug:production_plan_progress_id>/', views.update_ongoing_production_plan_progress, name='update_ongoing_production_plan_progress'),
    path('update_ongoing_production_stage/', views.update_ongoing_production_stage, name='update_ongoing_production_stage'),
    path('split_production_plan/<slug:production_plan_progress_id>/', views.split_production_plan, name='split_production_plan'),
    path('delete_production_plan/<slug:production_plan_progress_id>/', views.delete_production_plan, name='delete_production_plan'),
    path('sewing_planner_calendar', views.sewing_planner_calendar, name='sewing_planner_calendar'),
    path('set_sewing_start_dates_ajax', views.set_sewing_start_dates_ajax, name='set_sewing_start_dates_ajax'),
    path('delete_sewing_start_dates_ajax', views.delete_sewing_start_dates_ajax, name='delete_sewing_start_dates_ajax'),
    path('get_ppp_3_statuses_ajax', views.get_ppp_3_statuses_ajax, name='get_ppp_3_statuses_ajax'),
    path('set_ppp_3_statuses_ajax', views.set_ppp_3_statuses_ajax, name='set_ppp_3_statuses_ajax'),

    path('find_product_information_by_fnsku', views.find_product_information_by_fnsku, name='find_product_information_by_fnsku'),
    path('update_product_chinese_name_by_uploading', views.update_product_chinese_name_by_uploading, name='update_product_chinese_name_by_uploading'),
    path('update_transparency_label_required_sku_by_uploading', views.update_transparency_label_required_sku_by_uploading, name='update_transparency_label_required_sku_by_uploading'),

    path('amazon_authorization', amazon.amazon_authorization, name='amazon_authorization'),
    path('generate_transaction_report', amazon.generate_transaction_report, name='generate_transaction_report'),
    # path('generate_transaction_report_sdk', amazon.generate_rpt_using_sdk, name='generate_transaction_report_sdk'),
    path('read_csv_and_process_report', amazon.read_csv_and_process_report, name='read_csv_and_process_report')

]
