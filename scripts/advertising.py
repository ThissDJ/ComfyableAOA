"""
python manage.py runscript advertising
"""

import time
import os
import pytz
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
    def __init__(self, params: dict) -> None:
        self.params = params
    
    @property
    def client(self) -> Reports:
        return Reports(**self.params)
    
    def post_report(self):
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
            body=data
        )
        print(resp.payload)
    
    def get_report(self, report_id: str):
        resp = self.client.get_report(reportId=report_id)
        print(resp.payload)

    def download_report(self, url):
        self.client.download_report(url=url, file=f"{BASE_DIR}/scripts/ad_report", format='json')


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
        fba_shipemnt, _ = FbaShipmentVJ.objects.update_or_create(
            defaults={
                'shipment_name': shipment['ShipmentName'],
                'country': country,
                # 'shipped_product_sku_qties': shipped_product_sku_qties,
                'closed': shipement_closed_dict.get(shipment['ShipmentId'], True)
            },
            shipment_id=shipment['ShipmentId'],
        )
        fba_shipemnt.shipped_product_sku_qties.set(shipped_product_sku_qties)
        fba_shipemnt.save()


def run():
    # update_shipment(params=dict(credentials=au_credentials, marketplace=Marketplaces.AU), country="AU")
    # update_shipment(params=dict(credentials=us_credentials, marketplace=Marketplaces.US), country="US")
    client = ReportsClient(
        params=dict(credentials=us_ad_credentials, marketplace=AdMarketplaces.US)
    )
    # client.post_report()
    # client.get_report(report_id="5441528b-f78c-449b-96b1-1956ef8a5466")
    client.download_report(url='https://offline-report-storage-us-east-1-prod.s3.amazonaws.com/5441528b-f78c-449b-96b1-1956ef8a5466-1708931157903/report-5441528b-f78c-449b-96b1-1956ef8a5466-1708931157903.json.gz?X-Amz-Security-Token=IQoJb3JpZ2luX2VjEM%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIELldZ4LEAIpJzLnrCmyjyLSeycIsCQGjDb1TZjdHFLOAiEAkAzVTwWJTOt6mhkX2%2F0bX%2FKRCuzv%2FBoPMMphheM6rL4q6gUIuP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARACGgw4NDE2NDU1NDMwNzQiDO9MY84DjYA69f2o9yq%2BBcGYoq%2BzRvOT6qXrJ73yDVwwbt3hceGz5erMIz0pR%2BWZlkKKMU5P%2B3b96mIEUWnkWFsxVb%2FYhoUCaw4nwljNR6d2Qge1N424ZwsvS%2F4fT5vDeWxMMPh0ZE0HBXwWOPkI2J1EsVp6xbgwAFjOj6GDv020U90NuAdPaO6Zx1aPzOHFZvhpfvFczM5P31r3lmVpPXXwiUgxdpxc9Pq5xQIPVJ%2F8e11hzSEr3Oc%2B0kB9Ng78YTCLCWhfNnjGouFlzeg8KbV6%2FSBIteZDtw9TDNa2%2FHB5ENCziuOxwnQSrfY8vlKueiPrw%2Fg2oKlYJMKdin%2FTuU2dVaEWbb6yMGPK49TFFCa9cZeDD1Lo3tbGR8AGuYFFMKzgZbO8Pt8MNRQuwM41TAawwKVY%2Fg8w1t0%2BaWfwkDy%2BiFoBEvBMRlci8qkBAAAhq%2Bju5irRUlx8ghBPD9t0f%2B5IgDRi95eZrLBJsxWWTS8FtL2tyLXuBsgP%2BLhbSCwcSHGS1pOUh2TPLrJXdvb6Phh2QaXG%2BZWTFql7qzof5x3HpyejUqVHyQ0AwMhQnVjbkX%2FuGqeIeSDJz1fN298hlHWrxuVlMTDlDyr5JtRxYwIjHwWJ4XbVike5XCIgQn04Xm9B9QBgEwh3bIoKreyfNJgPKUrKTQ1JBGlcCZQGZlAnWrtFm69JN%2FmieS6di1aEiVOv6x1qyoY%2FOus9cnhvZvsrX4ftgLk5lM6nlVjimHkiggf1XRBDIi%2FT9huOQdXlSRvkg%2BEUKyJL4Ge0FOiZMsjWwHQiCvsiIwwFjB36fB%2FD7Kl1fgAPof7MkFZCcKf1MhLZ8tgl4nhE68ga2LVWkQPxfs6DyJNjncAipSbaa0%2FfQp%2FzSp5Noq%2Bw%2Fxb%2F%2BRV2miHBKCXKicRUJPlQ7GBDuCbg3QON%2FCqgH8buy4g2wSh27FhxHSQtwF4fap5CUDDM3%2FCuBjqpAS4yUAiUfFVdp0aEknZ4KWP4ZrZ4OfzDFUbeQ0MDzSKj9izMBZ0v2CQFNkyR5T4kQbjU%2FDh8FxxI6UsBvByJPkmwemGtv2FKix4hqMHc%2B2Pt%2FXvEbWmKgTXOgbxDkfYij9OSc7%2BqLIZvIxjlKQ80vA19DEiXJ2rXVINyZ3WMbHoBn9h%2BxqwkcZl8xLYC64KXO2kdO5swOEwnu%2FzrUugC8%2BAO7Y%2B8JFL7H18%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20240226T070750Z&X-Amz-SignedHeaders=host&X-Amz-Expires=3600&X-Amz-Credential=ASIA4H5P3Z2ROSRU34OB%2F20240226%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=a79a1f6023fa548a5f1151ddf0203b391ae046d2012c3d3f81571f599d958e5f')
