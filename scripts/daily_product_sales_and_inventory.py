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


def get_orders():
    order_client = Orders(credentials=au_credentials, marketplace=Marketplaces.AU)
    orders = order_client.get_orders(
        CreatedAfter=datetime.now(la_timezone).date(),
    )
    print(dict(orders))


def run():
    print('1' * 100)
    get_orders()