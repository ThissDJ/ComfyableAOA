from salesMonitor.models import ShippedProductSkuQty, FbaShipmentVJ, ShippedReceivedSkuQty
from django.db import connection


def run():
    print(ShippedProductSkuQty.objects.all().delete())
    print(ShippedReceivedSkuQty.objects.all().delete())
    print(FbaShipmentVJ.objects.all().delete())

    with connection.cursor() as cursor:
        # 清空表salesMonitor_fbashipmentvj_shipped_product_sku_qties
        cursor.execute('DELETE FROM salesMonitor_fbashipmentvj_shipped_product_sku_qties')
        cursor.execute('SELECT * FROM salesMonitor_fbashipmentvj_shipped_product_sku_qties')

        print(cursor.fetchall())