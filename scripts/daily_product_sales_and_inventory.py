"""
运行方式
`python manage.py runscript daily_product_sales_and_inventory`
"""

import json
import os
import time
import pytz
from dotenv import load_dotenv
from sp_api.api import Orders, Inventories, Sales, ReportsV2
from sp_api.base import Marketplaces, Granularity, ReportType, ProcessingStatus
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


def get_report_document_detail(client: ReportsV2, document_id: str, key="Merchant SKU"):
    if not document_id:
        return {}

    client.get_report_document(
        reportDocumentId=document_id,
        download=True,
        file=f"{BASE_DIR}/scripts/report.txt",
        character_code='iso-8859-1',
    )

    sku_doc_dict = {}
    with open(f"{BASE_DIR}/scripts/report.txt", encoding='iso-8859-1') as f:
        readlines = f.readlines()
        header = readlines[0]
        header = [head.replace('\n', '') for head in header.split('\t')]
        for line in readlines[1:]:
            doc = dict(zip(header, [li.replace('\n', '') for li in line.split('\t')]))
            sku_doc_dict[doc[key]] = doc
    
    return sku_doc_dict


def get_document_id(client: ReportsV2, report_id: str):
    report = client.get_report(reportId=report_id)
    print(report.payload)
    if report.payload["processingStatus"] in (ProcessingStatus.FATAL.value, ProcessingStatus.CANCELLED.value):
        return
    elif report.payload["processingStatus"] != ProcessingStatus.DONE.value:
        time.sleep(10)
        get_document_id(client, report_id)
    else:
        return report.payload["reportDocumentId"]


def get_order_ids(init_client_params):
    objs = []
    date = datetime.now(la_timezone).date()

    report_client = ReportsV2(**init_client_params)
    # 获取sku,asin
    # inventory = report_client.create_report(
    #     reportType=ReportType.GET_AFN_INVENTORY_DATA,
    #     dataStartTime=datetime.now(la_timezone).date().isoformat(),
    # )
    # time.sleep(1)
    # # 获取days_of_supply_by_amazon,recommended_replenishment_qty
    # recommend = report_client.create_report(
    #     reportType=ReportType.GET_RESTOCK_INVENTORY_RECOMMENDATIONS_REPORT,
    #     dataStartTime=datetime.now(la_timezone).date().isoformat(),
    # )

    time.sleep(30)
    # print(inventory.payload['reportId'], recommend.payload['reportId'])
    inventory_document_id = get_document_id(report_client, "292314019751")
    recommend_document_id = get_document_id(report_client, "292315019751")

    sku_inventory_dict = get_report_document_detail(report_client, inventory_document_id, key='seller-sku')
    sku_recommend_dict = get_report_document_detail(report_client, recommend_document_id, key='Merchant SKU')
    
    seller_skus = []
    for sku, item in sku_inventory_dict.items():
        objs.append({
            'sku': sku,
            'asin': item['asin'],
            'date': date,
            'days_of_supply_by_amazon': sku_recommend_dict.get(sku, {}).get('Total Days of Supply (including units from open shipments)') or '0',
            'recommended_replenishment_qty': sku_recommend_dict.get(sku, {}).get('Recommended replenishment qty') or '0',
            'inbound_unit': int(sku_recommend_dict.get(sku, {}).get('Inbound') or 0),
            'available': int(sku_recommend_dict.get(sku, {}).get('Available') or 0),
            'total_unit': int(sku_recommend_dict.get(sku, {}).get('Total Units') or 0),
            'fnsku': sku_recommend_dict.get(sku, {}).get('FNSKU') or '',
            'inbound_fc_unit': int(sku_recommend_dict.get(sku, {}).get('Working') or 0) + int(sku_recommend_dict.get(sku, {}).get('Shipped') or 0),
            'fc_unit': int(sku_recommend_dict.get(sku, {}).get('FC transfer') or 0) + int(sku_recommend_dict.get(sku, {}).get('FC Processing') or 0),
            'country': sku_recommend_dict.get(sku, {}).get('Country') or '',
            'currency': sku_recommend_dict.get(sku, {}).get('Currency code') or '',
        })
        if int(sku_recommend_dict.get(sku, {}).get('Total Units') or 0) > 0:
            seller_skus.append(sku)
    
    # --------------------------库存--------------------------
    # inventories_client = Inventories(**init_client_params)
    # inventories_list = []

    # def get_inventory_summary_marketplace(skus, next_token=None):
    #     resp = inventories_client.get_inventory_summary_marketplace(
    #         details=True,
    #         sellerSkus=skus,
    #         NextToken=next_token,
    #     )
    #     inventories_list.extend(resp.payload['inventorySummaries'])
    #     if resp.next_token:
    #         get_inventory_summary_marketplace(skus, next_token=resp.next_token)

    #     return
    
    # for i in range(0, len(seller_skus), 50):
    #     get_inventory_summary_marketplace(skus=seller_skus[i: i + 50])

    # inventories_dict = {inventories['sellerSku']: inventories for inventories in inventories_list}
    # for obj in objs:
    #     inventories = inventories_dict.get(obj['sku'])
    #     if not inventories:
    #         continue
        
        # inventoryDetails = inventories['inventoryDetails']
        # obj['fnsku'] = inventories['fnSku']
        # 商品总库存
        # obj['total_unit'] = inventories['totalQuantity']
        # 可用库存
        # obj['available'] = inventoryDetails['fulfillableQuantity']
        # 运往配送中心的库存单位
        # obj['inbound_fc_unit'] = inventoryDetails['inboundWorkingQuantity'] + inventoryDetails['inboundShippedQuantity']
        # 配送中心的库存单位
        # obj['fc_unit'] = inventoryDetails['reservedQuantity']['fcProcessingQuantity'] + inventoryDetails['reservedQuantity']['pendingTransshipmentQuantity']
        # 在途库存
        # obj['inbound_unit'] = inventoryDetails['inboundReceivingQuantity'] + inventoryDetails['inboundShippedQuantity'] + inventoryDetails['inboundWorkingQuantity']

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
    
    print(f"seller_skus count={len(seller_skus)}")
    for sku in seller_skus:
        get_order_metrics(sku, days=6)
        get_order_metrics(sku, days=1)
        time.sleep(3)

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


def run():
    # get_order_ids(init_client_params_au)
    get_order_ids(init_client_params_us)
