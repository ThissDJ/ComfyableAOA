"""
运行方式
`python manage.py runscript daily_product_sales_and_inventory`
"""

import os
import pytz
from dotenv import load_dotenv
from sp_api.api import Orders, Inventories, Products, Sales
from sp_api.base import Marketplaces, Granularity
from datetime import datetime, timezone
from comfyableAOA.settings import BASE_DIR

load_dotenv(f"{BASE_DIR}/.env")
la_timezone = pytz.timezone('America/Los_Angeles')

au_credentials = dict(
    refresh_token=os.getenv("SELLING_PARTNER_APP_REFRESH_TOKEN_AU"),
    lwa_app_id=os.getenv("SELLING_PARTNER_APP_CLIENT_ID_AU"),
    lwa_client_secret=os.getenv("SELLING_PARTNER_APP_CLIENT_SECRET_AU")
)
init_client_params = dict(
    credentials=au_credentials,
    marketplace=Marketplaces.AU
)


def get_order_ids():
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
            'sold_qty': item['QuantityOrdered'],    # TODO 需要核实
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
        # 配送中心的库存单位 TODO 需要核实
        obj['fc_unit'] = inventoryDetails['reservedQuantity']['fcProcessingQuantity']
        # 已到达的库存
        obj['inbound_unit'] = inventoryDetails['inboundReceivingQuantity']




def run():
    get_order_ids()