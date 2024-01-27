"""
运行方式
`python manage.py runscript daily_product_sales_and_inventory`
"""

import os
import pytz
from dotenv import load_dotenv
from sp_api.api import Orders, Inventories, Products, Sales, Replenishment
from sp_api.base import Marketplaces, Granularity
from datetime import datetime, timezone, timedelta
from comfyableAOA.settings import BASE_DIR
from salesMonitor.models import DailyProductSalesAndInventory

load_dotenv(f"{BASE_DIR}/.env")
la_timezone = pytz.timezone('America/Los_Angeles')
utc_timezone = pytz.timezone('UTC')

au_credentials = dict(
    refresh_token=os.getenv("SELLING_PARTNER_APP_REFRESH_TOKEN_AU"),
    lwa_app_id=os.getenv("SELLING_PARTNER_APP_CLIENT_ID_AU"),
    lwa_client_secret=os.getenv("SELLING_PARTNER_APP_CLIENT_SECRET_AU")
)

us_credentials = dict(
    refresh_token=os.getenv("SELLING_PARTNER_APP_REFRESH_TOKEN_US"),
    lwa_app_id=os.getenv("SELLING_PARTNER_APP_CLIENT_ID_US"),
    lwa_client_secret=os.getenv("SELLING_PARTNER_APP_CLIENT_SECRET_US")
)

init_client_params_au = dict(
    credentials=au_credentials,
    marketplace=Marketplaces.AU
)

init_client_params_us = dict(
    credentials=us_credentials,
    marketplace=Marketplaces.US
)


def get_order_ids(init_client_params):
    objs = []

    payload_list = []
    order_client = Orders(**init_client_params)
    date = datetime.now(la_timezone).date()

    # get order list
    def get_orders(next_token=None):
        resp = order_client.get_orders(
            CreatedAfter=date,
            NextToken=next_token,
        )
        payload_list.extend(resp.payload['Orders'])
        if resp.next_token:
            get_orders(next_token=resp.next_token)

        return
    
    get_orders()

    seller_order_ids = [payload['SellerOrderId'] for payload in payload_list]

    # get order detail
    order_items = []
    for order_id in seller_order_ids:
        def get_order_items(next_token=None):
            resp = order_client.get_order_items(
                order_id=order_id,
                NextToken=next_token,
            )
            order_items.extend(resp.payload['OrderItems'])
            if resp.next_token:
                get_order_items(next_token=resp.next_token)

            return
        
        get_order_items()
    
    seller_skus = []
    for item in order_items:
        objs.append({
            'sku': item['SellerSKU'],
            'asin': item['ASIN'],
            'date': date,
        })
        seller_skus.append(item['SellerSKU'])
    
    # 库存
    inventories_client = Inventories(**init_client_params)
    inventories_list = []

    def get_inventory_summary_marketplace(skus, next_token=None):
        resp = inventories_client.get_inventory_summary_marketplace(
            details=True,
            sellerSkus=skus,
            NextToken=next_token,
        )
        inventories_list.extend(resp.payload['inventorySummaries'])
        if resp.next_token:
            get_inventory_summary_marketplace(skus, next_token=resp.next_token)

        return
    
    for i in range(0, len(seller_skus), 50):
        get_inventory_summary_marketplace(skus=seller_skus[i: i + 50])

    inventories_dict = {inventories['sellerSku']: inventories for inventories in inventories_list}
    for obj in objs:
        inventories = inventories_dict.get(obj['sku'])
        if not inventories:
            continue
        
        inventoryDetails = inventories['inventoryDetails']
        obj['fnsku'] = inventories['fnSku']
        # 商品总库存
        obj['total_unit'] = inventories['totalQuantity']
        # 可用库存
        obj['available'] = inventoryDetails['fulfillableQuantity']
        # 运往配送中心的库存单位 TODO 需要核实
        obj['inbound_fc_unit'] = inventoryDetails['inboundWorkingQuantity'] + inventoryDetails['inboundShippedQuantity']
        # 配送中心的库存单位
        obj['fc_unit'] = inventoryDetails['reservedQuantity']['fcProcessingQuantity'] + inventoryDetails['reservedQuantity']['pendingTransshipmentQuantity']
        # 在途库存
        obj['inbound_unit'] = inventoryDetails['inboundReceivingQuantity'] + inventoryDetails['inboundShippedQuantity'] + inventoryDetails['inboundWorkingQuantity']

    # --------------------------Products--------------------------
    # product_client = Products(**init_client_params)
    # sku_pricing_dict = {}

    # def get_competitive_pricing_for_skus(skus):
    #     resp = product_client.get_competitive_pricing_for_skus(seller_sku_list=skus)
    #     for p in resp.payload:
    #         sku_pricing_dict[p['SellerSKU']] = p
    
    # for i in range(0, len(seller_skus), 20):
    #     get_competitive_pricing_for_skus(skus=seller_skus[i: i + 20])

    # --------------------------Sales--------------------------
    sales_client = Sales(**init_client_params)
    sku_sales_7_dict = {}
    sku_sales_1_dict = {}
    
    def get_order_metrics(sku, days):
        now_utc = datetime.now(utc_timezone)
        end_utc = now_utc.replace(hour=23, minute=59, second=59, microsecond=0)  # 将当前时间设置为今天的最后一刻
        start_utc = end_utc - timedelta(days=days)
        # 转换UTC时间到America/Los_Angeles时区
        start_la = start_utc.astimezone(la_timezone)
        end_la = end_utc.astimezone(la_timezone)
        resp = sales_client.get_order_metrics(
            interval=(start_la, end_la),
            granularity=Granularity.TOTAL,
            sku=sku,
        )
        if days == 6:
            sku_sales_7_dict[sku] = resp.payload[0]
        else:
            sku_sales_1_dict[sku] = resp.payload[0]
        return
    
    for sku in seller_skus:
        get_order_metrics(sku, days=6)
        get_order_metrics(sku, days=1)

    for obj in objs:
        sales_7_dict = sku_sales_7_dict.get(obj['sku']) or {}
        sales_1_dict = sku_sales_1_dict.get(obj['sku']) or {}
        obj['sold_qty_average_7d'] = sales_7_dict.get('unitCount') or 0
        obj['average_price_7d'] = sales_7_dict.get('averageUnitPrice', {}).get('amount') or 0
        obj['sales_amount'] = sales_1_dict.get('totalSales', {}).get('amount') or 0
        obj['sold_qty'] = sales_1_dict.get('unitCount') or 0
    
    # save
    for obj in objs:
        DailyProductSalesAndInventory.objects.update_or_create(
            defaults=obj,
            sku=obj.pop('sku'),
            date=obj.pop('date'),
        )
    
    # days_of_supply_by_amazon, recommended_replenishment_qty


def run():
    get_order_ids(init_client_params_au)