"""
python manage.py runscript advertising
"""

import time
import os
import pytz
from dotenv import load_dotenv
from sp_api.api import FulfillmentInbound
from sp_api.base import Marketplaces
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
    update_shipment(params=dict(credentials=au_credentials, marketplace=Marketplaces.AU), country="AU")
    update_shipment(params=dict(credentials=us_credentials, marketplace=Marketplaces.US), country="US")
