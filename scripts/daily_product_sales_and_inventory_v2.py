"""
run
python manage.py runscript daily_product_sales_and_inventory_v2
"""
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import os
import time
from typing import List
import pytz
from dotenv import load_dotenv
from sp_api.api import Orders, Inventories, Sales, ReportsV2, Products
from sp_api.base import Marketplaces, Granularity, ReportType, ProcessingStatus
from datetime import datetime, timezone, timedelta
from comfyableAOA.settings import BASE_DIR
from salesMonitor.models import DailyProductSalesAndInventory, SkuFnSkuAsinCountry

load_dotenv(f"{BASE_DIR}/.env")
utc_timezone = pytz.timezone('UTC')
la_timezone = pytz.timezone('America/Los_Angeles')

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


def get_one_year_ago(days=365):
    now_utc = datetime.now(pytz.utc)
    now_la = now_utc.astimezone(pytz.timezone('America/Los_Angeles'))
    one_year_ago = now_la - timedelta(days=days)
    return one_year_ago.isoformat()


def get_now_date(zone):
    return datetime.now(zone).date()


class InventoriesClient:
    """库存相关"""
    def __init__(self, params: dict, start_time, sleep: int = 1) -> None:
        self.params = params
        self.start_time = start_time
        self.sleep = sleep
        self.payload = []
        print(f"InventoriesClient init... start_time={start_time}")

    @property
    def client(self) -> Inventories:
        return Inventories(**self.params)
    
    def get_inventory_summary_marketplace(self, next_token=None):
        try:
            resp = self.client.get_inventory_summary_marketplace(
                details=True,
                nextToken=next_token,
                startDateTime=self.start_time
            )
            self.payload.extend(resp.payload['inventorySummaries'])
            if resp.next_token:
                time.sleep(self.sleep)
                self.get_inventory_summary_marketplace(next_token=resp.next_token)
        except Exception as e:
            print(f"get_inventory_summary_marketplace err={e}")
        
        return self.payload
    

class ReportClient:
    """报告相关"""
    def __init__(self, params: dict, start_time) -> None:
        self.params = params
        self.start_time = start_time
        self.report_id = None
        self.document_id = None
        self.get_doc_sleep = 10
        self.file = f"{BASE_DIR}/scripts/report.txt"
        self.character_code = "iso-8859-1"
        self.document_key = "Merchant SKU"
        self.document_dict = {}
        print(f"init ReportClient start_time={start_time}")

    def get_document_dict(self):
        s_time = int(time.time())
        self.create_report()
        print(f"create_report, diff_time={int(time.time())-s_time}, {self.report_id}")
        time.sleep(self.get_doc_sleep * 3)

        s_time = int(time.time())
        self.get_document_id()
        print(f"get_document_id, diff_time={int(time.time())-s_time}, {self.document_id}")

        s_time = int(time.time())
        self.get_document_detail()
        print(f"get_document_detail, diff_time={int(time.time())-s_time}")
        return self.document_dict

    @property
    def client(self) -> ReportsV2:
        return ReportsV2(**self.params)
    
    def create_report(self):
        try:
            resp = self.client.create_report(
                reportType=ReportType.GET_RESTOCK_INVENTORY_RECOMMENDATIONS_REPORT,
                dataStartTime=self.start_time,
            )
            self.report_id = resp.payload['reportId']
        except Exception as e:
            print(f"create_report err={e}")
        
        return self.report_id
    
    def get_document_id(self):
        if not self.report_id:
            self.document_id = None
            return
        
        try:
            resp = self.client.get_report(
                reportId=self.report_id
            )
            if resp.payload['processingStatus'] == ProcessingStatus.DONE.value:
                self.document_id = resp.payload['reportDocumentId']
            elif resp.payload['processingStatus'] in (ProcessingStatus.FATAL.value, ProcessingStatus.CANCELLED.value):
                self.document_id = None
            else:
                time.sleep(self.get_doc_sleep)
                self.get_document_id()
        except Exception as e:
            print(f"get_document_id err={e}")

        return self.document_id
    
    def get_document_detail(self) -> dict:
        if not self.document_id:
            return self.document_dict
        
        try:
            self.client.get_report_document(
                reportDocumentId=self.document_id,
                download=True,
                file=self.file,
                character_code=self.character_code,
            )
            with open(self.file, encoding=self.character_code) as f:
                readlines = f.readlines()
                header = readlines[0]
                header = [head.replace('\n', '') for head in header.split('\t')]
                for line in readlines[1:]:
                    doc = dict(zip(header, [li.replace('\n', '') for li in line.split('\t')]))
                    self.document_dict[doc[self.document_key]] = doc
        except Exception as e:
            print(f"get_document_detail err={e}")
        
        return self.document_dict
    

class SalesClient:
    """销售相关"""
    def __init__(self, params, asin_list: List[str]) -> None:
        self.params = params
        self.asin_list = asin_list
        self.days = 6
        self.sleep = 2.2
        self.err_sleep = 10
        self.sales_dict = {}
        self.aggregation_sale_dict = {}
        print(f"SalesClient init ..., asin_list count={len(asin_list)}")

    def get_aggregation_sale_dict(self):
        s_time = int(time.time())
        self.get_order_metrics()
        print(f"get_order_metrics, diff_time={int(time.time())-s_time}")
        self.aggregation_sales()
        return self.aggregation_sale_dict
    
    @property
    def client(self) -> Sales:
        return Sales(**self.params)
    
    @property
    def get_interval(self):
        now_utc = datetime.now(utc_timezone)
        end_utc = now_utc.replace(hour=23, minute=59, second=59, microsecond=0)  # 将当前时间设置为今天的最后一刻
        start_utc = end_utc - timedelta(days=self.days)
        start_la = start_utc.astimezone(la_timezone)
        end_la = end_utc.astimezone(la_timezone)
        return (start_la, end_la)
    
    def get_order_metrics(self):
        s_time = int(time.time())
        for asin in self.asin_list:
            try:
                resp = self.client.get_order_metrics(
                    interval=self.get_interval,
                    granularity=Granularity.DAY,
                    asin=asin,
                    granularityTimeZone="America/Los_Angeles"
                )
                self.sales_dict[asin] = resp.payload
            except Exception as e:
                print(f"get_order_metrics asin={asin}, err={e}")
                time.sleep(self.err_sleep)
                continue
            else:
                time.sleep(self.sleep)
        e_time = int(time.time())
        print(f"get_order_metrics 耗时：{s_time-e_time}秒, count={len(self.asin_list)}")
        return self.sales_dict
    
    def aggregation_sales(self):
        if not self.sales_dict:
            self.get_order_metrics()
        
        for asin, sales in self.sales_dict.items():
            sold_qty = sales[-1]['unitCount']
            sales_amount = sales[-1]['totalSales']['amount']
            sold_qty_average_7d = sum([s['unitCount'] for s in sales]) / len(sales)
            if sold_qty_average_7d:
                average_price_7d = sum([s['totalSales']['amount'] for s in sales]) / sum([s['unitCount'] for s in sales])
            else:
                average_price_7d = 0
            
            self.aggregation_sale_dict[asin] = {
                'sold_qty': sold_qty,
                'sales_amount': sales_amount,
                'sold_qty_average_7d': round(sold_qty_average_7d, 1),
                'average_price_7d': round(average_price_7d, 1),
            }
        return self.aggregation_sale_dict
    

def sum_asin_objs(asin_objs) -> dict:
    """合并相同asin下的sku"""
    # 找到原始sku
    seller_sku_obj = [o for o in asin_objs if not o['sku'].startswith('amzn.')]
    if not seller_sku_obj:
        return
    seller_sku_obj = seller_sku_obj[0]
    # seller_sku_obj['sold_qty'] = sum([o['sold_qty'] for o in asin_objs])
    # seller_sku_obj['sales_amount'] = sum([o['sales_amount'] for o in asin_objs])
    # seller_sku_obj['sold_qty_average_7d'] = sum([o['sold_qty_average_7d'] for o in asin_objs]) / len(asin_objs)
    # seller_sku_obj['average_price_7d'] = sum([o['average_price_7d'] for o in asin_objs]) / len(asin_objs)
    seller_sku_obj['total_unit'] = sum([o['total_unit'] for o in asin_objs])
    seller_sku_obj['available'] = sum([o['available'] for o in asin_objs])
    seller_sku_obj['inbound_fc_unit'] = sum([o['inbound_fc_unit'] for o in asin_objs])
    seller_sku_obj['fc_unit'] = sum([o['fc_unit'] for o in asin_objs])
    seller_sku_obj['inbound_unit'] = sum([o['inbound_unit'] for o in asin_objs])
    return seller_sku_obj


def update_today_sales_and_inventory(params, currency, country, date, inventory_days=365):
    # model DailyProductSalesAndInventory
    objs1 = []
    # model SkuFnSkuAsinCountry
    objs2 = []

    # 通过库存接口拿到一年内所有的asin
    inventories_client = InventoriesClient(params, start_time=get_one_year_ago(inventory_days))
    inventory_summaries = inventories_client.get_inventory_summary_marketplace()
    asin_dict = defaultdict(list)
    if not inventory_summaries:
        print("not inventory_summaries")
        return
    
    for inventory in inventory_summaries:
        asin_dict[inventory['asin']].append(inventory)
    
    # 获取7天内的平均价格
    sales_client = SalesClient(params, asin_list=list(asin_dict.keys()))
    aggregation_sale_dict = sales_client.get_aggregation_sale_dict()

    # 报告相关
    report_client = ReportClient(params, start_time=date.isoformat())
    document_dict = report_client.get_document_dict()

    asin_obj_dict = defaultdict(list)
    for inventory in inventory_summaries:
        inventoryDetails = inventory['inventoryDetails']
        asin_obj_dict[inventory['asin']].append({
            'sku': inventory['sellerSku'],
            'fnsku': inventory['fnSku'],
            'sold_qty': aggregation_sale_dict.get(inventory['asin'], {}).get('sold_qty') or 0,
            'sales_amount': aggregation_sale_dict.get(inventory['asin'], {}).get('sales_amount') or 0,
            'sold_qty_average_7d': aggregation_sale_dict.get(inventory['asin'], {}).get('sold_qty_average_7d') or 0,
            'average_price_7d': aggregation_sale_dict.get(inventory['asin'], {}).get('average_price_7d', {}) or 0,
            'date': date,
            'asin': inventory['asin'],
            'total_unit': inventory['totalQuantity'],
            'available': inventoryDetails['fulfillableQuantity'],
            'inbound_fc_unit': inventoryDetails['reservedQuantity']['fcProcessingQuantity'] + inventoryDetails['reservedQuantity']['pendingTransshipmentQuantity'] + inventoryDetails['inboundReceivingQuantity'] + inventoryDetails['inboundShippedQuantity'] + inventoryDetails['inboundWorkingQuantity'],
            'fc_unit': inventoryDetails['reservedQuantity']['fcProcessingQuantity'] + inventoryDetails['reservedQuantity']['pendingTransshipmentQuantity'],
            'inbound_unit': inventoryDetails['inboundReceivingQuantity'] + inventoryDetails['inboundShippedQuantity'] + inventoryDetails['inboundWorkingQuantity'],
            'days_of_supply_by_amazon': document_dict.get(inventory['sellerSku'], {}).get('Total Days of Supply (including units from open shipments)') or '0',
            'recommended_replenishment_qty': document_dict.get(inventory['sellerSku'], {}).get('Recommended replenishment qty') or '0',
            'currency': currency,
            'country': country,
        })
    
    for _, asin_objs in asin_obj_dict.items():
        asin_obj = sum_asin_objs(asin_objs)
        if not asin_obj:
            continue
        objs1.append(asin_obj)
        for o in asin_objs:
            if o['sku'] == asin_obj['sku']:
                continue
            objs2.append({
                'seller_sku': asin_obj['sku'],
                'sku': o['sku'],
                'asin': o['asin'],
                'fnsku': o['fnsku'],
                'country': o['country'],
            })
    
    for obj1 in objs1:
        DailyProductSalesAndInventory.objects.update_or_create(
            defaults=obj1,
            sku=obj1.pop('sku'),
            date=obj1.pop('date'),
        )
    
    for obj2 in objs2:
        SkuFnSkuAsinCountry.objects.update_or_create(
            defaults={},
            **obj2
        )
    print(f"update_today_sales_and_inventory done country={country}, update count={len(objs1)}")


def update_yesterday_sales(params, yesterday, country):
    """更新前一天的销售情况"""
    skus = DailyProductSalesAndInventory.objects.filter(
        date=yesterday,
        country=country,
    )
    asin_list = [s.asin for s in skus]
    if not asin_list:
        print(f"update_yesterday_sales not asin_list, yesterday={yesterday}")
        return
    sales_client = SalesClient(params, asin_list=list(asin_list))
    aggregation_sale_dict = sales_client.get_aggregation_sale_dict()
    for sku in skus:
        sku.sold_qty = aggregation_sale_dict.get(sku.asin, {}).get('sold_qty') or sku.sold_qty
        sku.sales_amount = aggregation_sale_dict.get(sku.asin, {}).get('sales_amount') or sku.sales_amount
        sku.sold_qty_average_7d = aggregation_sale_dict.get(sku.asin, {}).get('sold_qty_average_7d') or sku.sold_qty_average_7d
        sku.average_price_7d = aggregation_sale_dict.get(sku.asin, {}).get('average_price_7d') or sku.average_price_7d
        sku.save()
    print(f"update_yesterday_sales done country={country}, yesterday={yesterday}")


def do_work(params, currency, country, date, inventory_days):
    update_today_sales_and_inventory(params, currency=currency, country=country, date=date, inventory_days=inventory_days)
    update_yesterday_sales(params, yesterday=date - timedelta(days=1))


def run():
    while True:
        date = get_now_date(la_timezone)
        yesterday = date - timedelta(days=1)
        print(f"start run, date={date}")
        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.submit(update_today_sales_and_inventory, init_client_params_au, 'AUD', 'AU', date, 365)
            executor.submit(update_today_sales_and_inventory, init_client_params_us, 'USD', 'US', date, 365)

            executor.submit(update_yesterday_sales, init_client_params_au, yesterday, "AU")
            executor.submit(update_yesterday_sales, init_client_params_us, yesterday, "US")

        time.sleep(60 * 30)
