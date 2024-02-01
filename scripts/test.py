from salesMonitor.models import DailyProductSalesAndInventory
from django.db import connection


def run():
    # print(DailyProductSalesAndInventory.objects.filter())

    cursor = connection.cursor()
    cursor.execute("select * from django_migrations")
    raw = cursor.fetchall()
    print(raw)