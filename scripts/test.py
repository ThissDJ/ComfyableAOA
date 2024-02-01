from salesMonitor.models import DailyProductSalesAndInventory


def run():
    print(DailyProductSalesAndInventory.objects.filter())
