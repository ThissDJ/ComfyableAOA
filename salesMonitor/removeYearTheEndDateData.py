from salesMonitor.models import  Product, TodayProductSales, Last7dayProductSales, HistoryTodaySales, HistoryLast7dayProductSales,  HistoryTodayProductSales

import datetime
default_country = 'US'
todaySales = HistoryTodaySales.objects.filter(country=default_country).order_by('-date')[0]

today_sales_date = todaySales.date

HistoryTodaySales.objects.filter(date = today_sales_date)
HistoryLast7dayProductSales.objects.filter(date = today_sales_date)
TodayProductSales.objects.all()

HistoryTodayProductSales.objects.filter(date = today_sales_date).
