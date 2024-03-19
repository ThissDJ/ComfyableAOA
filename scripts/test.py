from salesMonitor.models import ShippedProductSkuQty, FbaShipmentVJ, ShippedReceivedSkuQty


def run():
    print(ShippedProductSkuQty.objects.all().delete())
    print(ShippedReceivedSkuQty.objects.all().delete())
    print(FbaShipmentVJ.objects.all().delete())
