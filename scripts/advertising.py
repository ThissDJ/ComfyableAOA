"""
python manage.py runscript advertising
"""
import json
import time
import os
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sp_api.api import FulfillmentInbound
from sp_api.base import Marketplaces
from ad_api.base import Marketplaces as AdMarketplaces
from ad_api.api.reports import Reports
from comfyableAOA.settings import BASE_DIR
from salesMonitor.models import FbaShipmentVJ, ReceivedSkuQtyVJ, Product, ShippedProductSkuQty


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
    def __init__(self, params: dict, start_date, end_date) -> None:
        self.params = params
        self.start_date = start_date
        self.end_date = end_date
        print(f"ReportsClient init ... start_date={start_date}, end_date={end_date}")
    
    @property
    def client(self) -> Reports:
        return Reports(**self.params)
    
    def post_report(self, body):
        data = """
            {
                "name":"SP campaigns report 2/1-2/1",
                "startDate":"2024-02-01",
                "endDate":"2024-02-02",
                "configuration":{
                    "adProduct":"SPONSORED_PRODUCTS",
                    "groupBy":["campaign"],
                    "columns":["cost","sales7d"],
                    "reportTypeId":"spCampaigns",
                    "timeUnit":"SUMMARY",
                    "format":"GZIP_JSON"
                }
            }
        """
        resp = self.client.post_report(
            body=body
        )
        return resp.payload
    
    def get_report(self, report_id: str):
        resp = self.client.get_report(reportId=report_id)
        print(resp.payload)

    def download_report(self, url):
        self.client.download_report(url=url, file=f"{BASE_DIR}/scripts/ad_report", format='json')

    def get_body(self, name, ad_product):
        body = {
                "name":name,
                "startDate": self.start_date,
                "endDate": self.end_date,
                "configuration":{
                    "adProduct": ad_product,
                    "groupBy": ["campaign"],
                    "columns": ["cost","sales7d", "startDate"],
                    "reportTypeId": "spCampaigns",
                    "timeUnit": "SUMMARY",
                    "format": "GZIP_JSON"
                }
            }
        return json.dumps(body)

    def get_report_detail(self):
        """
        需要生成SPONSORED_PRODUCTS、SPONSORED_BRANDS、SPONSORED_DISPLAY三种报告
        """
        body = self.get_body(name="SP display campaigns report", ad_product="SPONSORED_DISPLAY")
        print(self.post_report(body=body))


def update_shipment(params: dict, country: str):
    client = FulfillmentInboundClient(params=params)
    shipment_close_threshold = {
        'US': 15,
        'AU': 4
    }
    item_data = client.get_shipment_info()
    shipment_data = client.shipment_data
    shipement_sku_dict = client.shipement_sku_dict
    shipement_closed_dict = {}
    for item in item_data:
        # 未收货的数量
        unreceived = item['QuantityShipped'] - item['QuantityReceived']
        if unreceived >= shipment_close_threshold[country]:
            shipement_closed_dict[item['ShipmentId']] = False

        # update ReceivedSkuQtyVJ model
        ReceivedSkuQtyVJ.objects.update_or_create(
            defaults={'qty': item['QuantityShipped'] + item['QuantityReceived']},
            shipment_id=item['ShipmentId'],
            sku=item['SellerSKU'],
        )
    
        # update ShippedProductSkuQty model
        product = Product.objects.filter(sku=item['SellerSKU']).first()
        if product:
            ShippedProductSkuQty.objects.update_or_create(
                defaults={'qty': item['QuantityShipped'] + item['QuantityReceived']},
                sku=item['SellerSKU'],
                product=product,
            )

    for shipment in shipment_data:
        # update FbaShipmentVJ model
        shipped_product_sku_qties = ShippedProductSkuQty.objects.filter(
            sku__in=shipement_sku_dict.get(shipment['ShipmentId'], [])
        ).all()
        fba_shipment, _ = FbaShipmentVJ.objects.update_or_create(
            defaults={
                'shipment_name': shipment['ShipmentName'],
                'country': country,
                # 'shipped_product_sku_qties': shipped_product_sku_qties,
                'closed': shipement_closed_dict.get(shipment['ShipmentId'], True)
            },
            shipment_id=shipment['ShipmentId'],
        )
        fba_shipment.shipped_product_sku_qties.set(shipped_product_sku_qties)
        fba_shipment.save()


def run():
    # update_shipment(params=dict(credentials=au_credentials, marketplace=Marketplaces.AU), country="AU")
    # update_shipment(params=dict(credentials=us_credentials, marketplace=Marketplaces.US), country="US")
    start_date = get_now_date(la_timezone) - timedelta(days=6)
    end_date = get_now_date(la_timezone)
    client = ReportsClient(
        params=dict(credentials=us_ad_credentials, marketplace=AdMarketplaces.US),
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
    )
    client.get_report_detail()
    # client.post_report()
    # client.get_report(report_id="5441528b-f78c-449b-96b1-1956ef8a5466")
    # client.download_report(url='https://offline-report-storage-us-east-1-prod.s3.amazonaws.com/5441528b-f78c-449b-96b1-1956ef8a5466-1708931157903/report-5441528b-f78c-449b-96b1-1956ef8a5466-1708931157903.json.gz?X-Amz-Security-Token=IQoJb3JpZ2luX2VjENb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJGMEQCIGn4pDhSuE3hhoONYWTVnE7umQPgLYOWdaNVSP8gQzPoAiA9TGM1fbUUdbrJrp8M2OMkg9WqjVlfF8shzNzdToxe4CrqBQi%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAIaDDg0MTY0NTU0MzA3NCIMXOzAxo2US2gZlPvpKr4FJGKcujWSxPP3a6GMZJyCMlIfMWtphM7ahi1%2FTx6NVRqzpEe4FcIN0rkDKQ0i476ky6P20%2B0xX7LLNTaoqcYquim8fApMH07YbOZ8H7175KF6UMc592KMSenCucEMFspyjWwoK36qD0SAsot9LV1Ex8PTbIoib9wgkBV3w2d7XuO9nbWLrZBD%2FZF6%2FDlYUej6T4loYnm7r5ztHM3tnFyfXqQd3Cmq4Pm5n8Cfe4ZrOqjkaITU6kKEvjbddALue7mQ9iUPynIX58XcIOn2rIX29IdkelHj%2FgszeThscqtw1EUGsomvvpl0cN0ty1j%2BmgX4y%2FFkYNAT%2BXrKiYLLG7DuRq1duwRC0cZa5g8FrJiMVnwjv70G5PxMxEEu4%2BE32Yd3L%2BeAODR%2Fp%2Bq7k3loDrE7oNL0RGxjqC3r%2Ba9wB%2F8fKrKYIeVMvauwnIzaRNu%2FsSvbfNWEX%2B9LIxd%2BVJcB7Ndomoi9m3PMzXrx3VF8sUJxffodLpAoddwyiXsrYnE4DbDDNWCH7J7Zj0uMbnLfp6rcxxrZpqUlFfaL62wP5CuHN%2BkIzFZ4hZjreDT8diWsfvGzFHn1h0yjPpyz5JMxZIHbfecosjDXGYApjJD%2F2zf2r4iqpa3ClcaHMB%2Buh2sq3IshZ1dyFbdcENQvQwA1tNs1tZqTdS44WgYfGnelMxUeO3EGarzzcZ5ivIS9Qx5XffxBO%2FF%2BeY%2Fn44CzFfKgbyPv9bg3HugFMmFriZmD4YXXQvRDNqiY3Usr%2F2guZhAxESQa10%2F4Mz8tOVT%2B5sQ%2BooZZEjZh%2FV8inEMqkWc16BqVT%2B2u41bxrAykyA3XDFRg4yM1wbDLNBQfdyOqL%2FIynYaYIXjdXNaxOJcldSEPx3SFni8Kx2Y7s0d40187uhTYkqgGkchx4PG0mFu2QRm3nywds3dg5XeR79TJqAnud4uPMPqg8q4GOqoBCH0WUZKA1fp8K0PE9q4jCrS7m0Ovtpb9SNuhtN4KHjNxylmX0dXF2gdGazQdK2YykQYncEgreB87W9dA4RaEzZGcJLNcj3i1S%2FUzeciR6v%2B6U%2BkJZ1INe%2BAlfyxvIdcVIopepLhMADFm0PYNdCzL0z4IJ3IJu%2FKIOI3E%2Bu2xsdL%2FW6QNqQKN9zBYwEcoFzNZU%2F5AxhO%2BAaoEan8Sghcz3MW7LF2SvWv4tVY%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20240226T134455Z&X-Amz-SignedHeaders=host&X-Amz-Expires=3600&X-Amz-Credential=ASIA4H5P3Z2RBQB6SZG4%2F20240226%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=5eb0f0c55294b00bbffd025e2cbe3e0e9da1bc79a80826b91fabf823d023da49')
