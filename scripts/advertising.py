"""
python manage.py runscript advertising
"""
import json
import time
import os
import pytz
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sp_api.api import FulfillmentInbound
from sp_api.base import Marketplaces
from ad_api.base import Marketplaces as AdMarketplaces
from ad_api.api.reports import Reports
from comfyableAOA.settings import BASE_DIR
from salesMonitor.models import AdPerformaceDaily, FbaShipmentVJ, ShippedReceivedSkuQty


utc_timezone = pytz.timezone('UTC')
la_timezone = pytz.timezone('America/Los_Angeles')

load_dotenv(f"{BASE_DIR}/.env")
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

au_ad_credentials = dict(
    refresh_token=os.getenv("SELLING_PARTNER_APP_REFRESH_TOKEN_AU"),
    client_id=os.getenv("SELLING_PARTNER_APP_CLIENT_ID_AU"),
    client_secret=os.getenv("SELLING_PARTNER_APP_CLIENT_SECRET_AU"),
    profile_id=os.getenv("AD_API_PROFILE_ID_AU")
)

us_ad_credentials = dict(
    refresh_token=os.getenv("SELLING_PARTNER_APP_REFRESH_TOKEN_US"),
    client_id=os.getenv("SELLING_PARTNER_APP_CLIENT_ID_US"),
    client_secret=os.getenv("SELLING_PARTNER_APP_CLIENT_SECRET_US"),
    profile_id=os.getenv("AD_API_PROFILE_ID_US")
)


def get_now_date(zone):
    return datetime.now(zone).date()


class FulfillmentInboundClient:
    """货件相关"""
    def __init__(self, params: dict) -> None:
        self.params = params
        self.sleep = 0.6
        self.shipment_data = []
        self.item_data = []
        self.shipement_sku_dict = {}
        self.shipment_status_list = ['WORKING', 'READY_TO_SHIP', 'SHIPPED', 'RECEIVING', 'IN_TRANSIT', 'DELIVERED', 'CHECKED_IN']
        print("FulfillmentInboundClient init...")

    @property
    def client(self) -> FulfillmentInbound:
        return FulfillmentInbound(**self.params)
    
    def get_shipments(self):
        try:
            resp = self.client.get_shipments(
                QueryType="SHIPMENT",
                ShipmentStatusList=','.join(self.shipment_status_list),
            )
            self.shipment_data.extend(resp.payload['ShipmentData'])
        except Exception as e:
            print(f"get_shipments err={e}")
        return self.shipment_data
        
    def shipment_items_by_shipment(self, shipment_id):
        try:
            resp = self.client.shipment_items_by_shipment(
                shipment_id=shipment_id,
            )
            self.item_data.extend(resp.payload['ItemData'])
            self.shipement_sku_dict[shipment_id] = [x['SellerSKU'] for x in resp.payload['ItemData']]
        except Exception as e:
            print(f"shipment_items_by_shipment err={e}")
        return self.item_data
    
    def get_shipment_info(self):
        shipment_data = self.get_shipments()
        shipment_id_dict = {s['ShipmentId']: s['ShipmentName'] for s in shipment_data}
        for shipment in shipment_data:
            self.shipment_items_by_shipment(shipment_id=shipment['ShipmentId'])
            time.sleep(1)
        for item in self.item_data:
            item["ShipmentName"] = shipment_id_dict.get(item['ShipmentId'])
        return self.item_data
    

class ReportsClient:
    """广告相关"""
    def __init__(self, params: dict, start_date: str, end_date: str, country: str) -> None:
        self.params = params
        self.start_date = start_date
        self.end_date = end_date
        self.country = country
        self.base_file = f"{BASE_DIR}/scripts/{self.country}_"
        # 记录报告数据
        self.display_data = []
        self.product_data = []
        self.brands_data = []
        self.url = ''
        print(f"ReportsClient {country} init ... start_date={start_date}, end_date={end_date}")
    
    @property
    def client(self) -> Reports:
        return Reports(**self.params)
    
    def post_report(self, body):
        """
        {'configuration': {'adProduct': 'SPONSORED_DISPLAY', 'columns': ['cost', 'sales', 'startDate'], 'filters': None, 'format': 'GZIP_JSON', 'groupBy': ['campaign'], 'reportTypeId': 'sdCampaigns', 'timeUnit': 'SUMMARY'}, 'createdAt': '2024-02-28T03:56:24.397Z', 'endDate': '2024-02-27', 'failureReason': None, 'fileSize': None, 'generatedAt': None, 'name': 'SP display campaigns report', 'reportId': '3f058019-ec9f-4e46-b2be-1959d6214f90', 'startDate': '2024-02-21', 'status': 'PENDING', 'updatedAt': '2024-02-28T03:56:24.397Z', 'url': None, 'urlExpiresAt': None}
        """
        try:
            resp = self.client.post_report(
                body=body
            )
            print(f"[{self.country}]post_report reportId={resp.payload['reportId']}")
            return resp.payload['reportId']
        except Exception as e:
            print(f"post_report err {e}")
        
        return ""
    
    def get_report(self, report_id: str, retry_num=120):
        """
        {'configuration': {'adProduct': 'SPONSORED_DISPLAY', 'columns': ['cost', 'sales', 'startDate'], 'filters': None, 'format': 'GZIP_JSON', 'groupBy': ['campaign'], 'reportTypeId': 'sdCampaigns', 'timeUnit': 'SUMMARY'}, 'createdAt': '2024-02-28T03:56:24.397Z', 'endDate': '2024-02-27', 'failureReason': None, 'fileSize': 72, 'generatedAt': '2024-02-28T03:57:30.409Z', 'name': 'SP display campaigns report', 'reportId': '3f058019-ec9f-4e46-b2be-1959d6214f90', 'startDate': '2024-02-21', 'status': 'COMPLETED', 'updatedAt': '2024-02-28T03:57:30.409Z', 'url': 'https://offline-report-storage-us-east-1-prod.s3.amazonaws.com/3f058019-ec9f-4e46-b2be-1959d6214f90-1709092589834/report-3f058019-ec9f-4e46-b2be-1959d6214f90-1709092589834.json.gz?X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPz%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIQDTiVo0Q%2FzVvASPCtI7lpdjN4VqmAnxDsJVxNtVxvAh4wIgQO61G2KI4%2FanBE0mQFHbs8okalLDEeRP5z3z37Lh7Jsq6gUI5P%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARACGgw4NDE2NDU1NDMwNzQiDF9XksyaMO4pqVprXCq%2BBZ9%2FZAJWxDMx5CeqD9rpYHCJpouUqJTnhPPmm0nhiJzxAa6545pzHQWFV0Zq6hzxzlwwnvbYjbLXhOuQq%2BUC%2FiN8CjiF0GXJhH3pu24FVM8czCbxFQ4%2BnyUHxvutNwXDEvTPaFF0jchNV5DPaY7sLBNkI84OnUlTWGMGONplOo5xg2C8QIOcf1%2F5uLg%2FrNoO7b0qtO5SxkNDcXCxG9egLAx9LXoNHII%2BKoOiPYh5Xd02XsY1fLcle1XO3izwCBm7ubke6kOMvCBN3e5kHGd48nFuXFL3TQGeZ9rukSo0RJs82Y%2F4dh%2BWN2Y64nJiU0fd%2FDOK2ab6NfW2JXc7QDnQvX5Pq8s5%2FiPUBljxid2otN3Dci14DfudDPrsTQqpjY%2Fki3dQLlIPYYMl0w9OnmniOSganWBhrBG8d73JE%2BflQOO8f9bkuOqitVUAfsA9jPpaG45w%2FsY3Q%2F9Q5Hmyagfk9kCbmVbJdTK8s%2BGTrD8YWJv6qLevqPVYmCuHKQndTZ0HRF6U7Kv4axTYQ55CcaNt%2BvE0ZJsdvXfLvqutpPyuh6HsP9dm2XVsKxd1o93tnF%2F%2FkHaEKhwSxeaICInUNx58QN7ee2%2Fm2mMBwo0JRg0utFYZNSxVT0cePdpvJzg%2Bf5NYzSBk7WsO0CmSRZW6lfg%2B8utwcgc%2BdQMsGRY1pA7pJHubbuxXc891d6QXvuYSO7RqRNOVzIEcwEGRsRWxKgsa3W82er%2BdHJlNBcTjvJJNa7ddx0gEZXVE94IrNaSc6vGCr8bEf%2BHuNlf1m8wvodRAhcs%2Fs8%2FQEgNrHFlbndFKCrhgVa%2FTlyVDJPARbzJqSI%2BM5NamBAyBBWy1cVFrN1ZUoln1UuVp6XlZKOvc7W9kJ8tu6shdkOhQDb6B8CWUvv1NQyvVKlUn9Z%2FK5pegm52I%2B63rlIdDV3jCcZQem40YATCdzfquBjqpAbYnsmw8VTO3k2S5b2f%2Fb0o8gH7ld1Hg8a548JigpRCMl%2FAOIeCsqmF2wHfVDCazBF4lM%2BTOf2Mg3IjrmdU9P5W4MZx2DfS%2Bk2nEK2I2AqrBnMajLenvvWP6tTFGCBDnmBqzIaabwyEIEd2XN0uT7F8bju5YeF%2BP0PnJaebiJW8maZ2UHk9p%2Boa7i7kUwSHwNgW4Dm7BxtT4xDOOUpODKPlc8LKTuQZyQao%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20240228T035731Z&X-Amz-SignedHeaders=host&X-Amz-Expires=3599&X-Amz-Credential=ASIA4H5P3Z2REL37ZC55%2F20240228%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=0816d0140427aebc15c1929a666085ed075a678d1a77a9cfa94c27af72fa1f2e', 'urlExpiresAt': '2024-02-28T04:57:31.364988Z'}
        """
        try:
            resp = self.client.get_report(reportId=report_id)
            if resp.payload['url']:
                print(f"[{self.country}] [{retry_num}] get_report [{resp.payload}]")
                self.url = resp.payload['url']
                return self.url
            elif retry_num > 0:
                retry_num -= 1
                print(f"[{self.country}] [{retry_num}] get_report retry {resp.payload}")
                time.sleep(60)
                self.get_report(report_id=report_id, retry_num=retry_num)
            else:
                print(f"重试结束，未能获取到报告，{report_id}, {resp.payload}")
                return ''
        except Exception as e:
            print(f"get_report err {e}")
        return ''

    def download_report(self, url, filename):
        try:
            resp = self.client.download_report(
                url=url,
                file=f"{self.base_file}{filename}_report",
                format='json'
            )
            print(f"[{self.country}] {resp.payload} [{url}]")
        except Exception as e:
            print(f"download_report err {e}")

    def get_body(self, name, ad_product, report_type_id, columns=None):
        body = {
            "name": name,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "configuration": {
                "adProduct": ad_product,
                "groupBy": ["campaign"],
                "columns": columns or ["cost", "sales", "date"],
                "reportTypeId": report_type_id,
                "timeUnit": "DAILY",
                "format": "GZIP_JSON"
            }
        }
        return json.dumps(body)
    
    def get_name(self, prefix):
        start_date = self.start_date.replace('-', '/')[5:]
        end_date = self.end_date.replace('-', '/')[5:]
        return f"{prefix} {start_date}-{end_date}"
    
    def get_display_report(self):
        name = self.get_name(prefix="SD campaigns report")
        display_body = self.get_body(
            name=name,
            ad_product="SPONSORED_DISPLAY",
            report_type_id="sdCampaigns"
        )
        report_id = self.post_report(body=display_body)
        if not report_id:
            print(f"{name} not report_id")
            return
        
        time.sleep(60)

        self.get_report(report_id=report_id)
        if not self.url:
            print(f"{name} not url")
            return
        
        time.sleep(5)
        self.download_report(url=self.url, filename="display")

        if not Path(f"{self.base_file}display_report.json").exists():
            print(f"{name} not display_report.json")
            return
        
        with open(f"{self.base_file}display_report.json", 'r', encoding='utf-8') as file:
            self.display_data = json.load(file)
        return
    
    def get_product_report(self):
        name = self.get_name(prefix="SP campaigns report")
        product_body = self.get_body(
            name=name,
            ad_product="SPONSORED_PRODUCTS",
            report_type_id="spCampaigns",
            columns=["cost", "sales1d", "date"]
        )
        report_id = self.post_report(body=product_body)
        if not report_id:
            print(f"{name} not report_id")
            return
        
        time.sleep(60)

        self.get_report(report_id=report_id)
        if not self.url:
            print(f"{name} not url")
            return
        
        time.sleep(5)
        self.download_report(url=self.url, filename="product")

        if not Path(f"{self.base_file}product_report.json").exists():
            print(f"{name} not product_report.json")
            return
        
        with open(f"{self.base_file}product_report.json", 'r', encoding='utf-8') as file:
            self.product_data = json.load(file)
        return
    
    def get_brands_report(self):
        name = self.get_name(prefix="SB campaigns report")
        brands_body = self.get_body(
            name=name,
            ad_product="SPONSORED_BRANDS",
            report_type_id="sbCampaigns"
        )
        report_id = self.post_report(body=brands_body)
        if not report_id:
            print(f"{name} not report_id")
            return
        
        time.sleep(60)

        self.get_report(report_id=report_id)
        if not self.url:
            print(f"{name} not url")
            return
        
        time.sleep(5)
        self.download_report(url=self.url, filename="brands")

        if not Path(f"{self.base_file}brands_report.json").exists():
            print(f"{name} not brands_report.json")
            return
        
        with open(f"{self.base_file}brands_report.json", 'r', encoding='utf-8') as file:
            self.brands_data = json.load(file)
        
        return

    def get_report_detail(self):
        """
        需要生成SPONSORED_PRODUCTS、SPONSORED_BRANDS、SPONSORED_DISPLAY三种报告
        """
        self.get_display_report()
        self.url = ''
        self.get_product_report()
        self.url = ''
        self.get_brands_report()
        self.display_data.extend(self.product_data)
        self.display_data.extend(self.brands_data)
        return self.display_data


def update_shipment(params: dict, country: str):
    client = FulfillmentInboundClient(params=params)
    shipment_close_threshold = {
        'US': 15,
        'AU': 4
    }
    item_data = client.get_shipment_info()
    shipment_data = client.shipment_data
    shipement_closed_dict = {}
    for item in item_data:
        # 未收货的数量
        unreceived = item['QuantityShipped'] - item['QuantityReceived']
        if unreceived >= shipment_close_threshold[country]:
            shipement_closed_dict[item['ShipmentId']] = False
    
    fba_shipment_dict = dict()
    for shipment in shipment_data:
        # update FbaShipmentVJ model
        fba_shipment, _ = FbaShipmentVJ.objects.update_or_create(
            defaults={
                'shipment_name': shipment['ShipmentName'],
                'closed': shipement_closed_dict.get(shipment['ShipmentId'], True)
            },
            shipment_id=shipment['ShipmentId'],
            country=country,
        )
        fba_shipment_dict[shipment['ShipmentId']] = fba_shipment
        deleted = ShippedReceivedSkuQty.objects.filter(fba_shopment_vj=fba_shipment).delete()
        print(f"delete {country} {fba_shipment}/{fba_shipment.shipment_id} [{deleted}]")
    for item in item_data:
        fba_shipment: FbaShipmentVJ = fba_shipment_dict[item['ShipmentId']]
        if fba_shipment.closed:
            continue
        ShippedReceivedSkuQty.objects.update_or_create(
            defaults={
                'shipped_qty': item['QuantityShipped'],
                'received_qty': item['QuantityReceived'],
                'unreceived_qty': max(0, item['QuantityShipped'] - item['QuantityReceived']),
                'country': country,
            },
            fba_shopment_vj=fba_shipment,
            sku=item['SellerSKU'],
        )
        
    print(f"[{country}] update_shipment finish!")


def update_ad_performace_daily(params: dict, start_date, end_date, country):
    client = ReportsClient(
        params=params,
        start_date=start_date,
        end_date=end_date,
        country=country
    )
    ad_list = client.get_report_detail()
    aggregated_data = {}
    for ad in ad_list:
        ad_sales = ad.get('sales') or ad.get('sales1d') or 0
        cost = ad.get('cost') or 0
        date = ad['date']
        if date in aggregated_data:
            aggregated_data[date]["ad_sales"] += ad_sales
            aggregated_data[date]["cost"] += cost
        else:
            aggregated_data[date] = {"ad_sales": ad_sales, "cost": cost}
    
    for date, data in aggregated_data.items():
        AdPerformaceDaily.objects.update_or_create(
            defaults=data,
            date=date,
            country=country,
        )
    print(f"[{country}] {aggregated_data} update finish!")


def async_update_shipment(params: dict, country: str):
    while True:
        try:
            update_shipment(params=params, country=country)
        except Exception as e:
            print(f"async_update_shipment {country} err {e}")
        finally:
            print(f"async_update_shipment {country} sleep...")
            time.sleep(30 * 60)


def async_update_ad_performace_daily(params: dict, country):
    while True:
        try:
            end_date = get_now_date(la_timezone)
            start_date = end_date - timedelta(days=6)

            start_date = start_date.strftime('%Y-%m-%d')
            end_date = end_date.strftime('%Y-%m-%d')
            update_ad_performace_daily(params=params, start_date=start_date, end_date=end_date, country=country)
        except Exception as e:
            print(f"async_update_ad_performace_daily {country} err {e}")
        finally:
            print(f"async_update_ad_performace_daily {country} sleep...")
            time.sleep(60 * 60)


def run():
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.submit(async_update_shipment, dict(credentials=au_credentials, marketplace=Marketplaces.AU), "AU")
        executor.submit(async_update_shipment, dict(credentials=us_credentials, marketplace=Marketplaces.US), "US")
        executor.submit(async_update_ad_performace_daily, dict(credentials=us_ad_credentials, marketplace=AdMarketplaces.US), "US")
        executor.submit(async_update_ad_performace_daily, dict(credentials=au_ad_credentials, marketplace=AdMarketplaces.AU), "AU")
