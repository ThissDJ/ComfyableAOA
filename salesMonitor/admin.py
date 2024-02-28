from django.contrib import admin

from .models import DownloadedReport, FbaShipmentVJ, PaymentTransactionDetail, Product, ReceivedSkuQtyVJ, ShippedProductSkuQty, TodayProductSales, Last7dayProductSales, \
    DailySalesLastYear, FbaInventory, Inventory, ReceivablePurchasedQty, FulfillmentCenterCodeCountry, \
    HistoryTodayProductSales, HistoryTodaySales, \
    FbaShipment, ShippedSkuQty, ReceivedSkuQty, RemoteFulfillmentSku, Upc, SkuUpc, FbaShipmentPaidBill, \
    NearestReceivablePurchasedQty, \
    Supplier, UserSupplier, SkuSupplier, SkuPurchasingPrice, SkuHeadShippingUnitCost, \
    SkuAssetLiabilityTable, SkuManagedBySalesPerson, FbaShipmentCost, SkuPurchaseOrder, \
    ProfitLossTable, \
    CurrencyRate, \
    ProductionPlanProgress, ProductionStage, ProductionPlanProgress, ProductionStageTypeParameter, \
    SkuProductionStageTypeParameter, DailyProductSalesAndInventory, SkuFnSkuAsinCountry, AdPerformaceDaily

# admin.site.register(Product)
admin.site.register(TodayProductSales)
admin.site.register(Last7dayProductSales)
admin.site.register(DailySalesLastYear)
admin.site.register(FbaInventory)
admin.site.register(RemoteFulfillmentSku)
admin.site.register(Inventory)
admin.site.register(ReceivablePurchasedQty)
admin.site.register(FbaShipment)
admin.site.register(ShippedSkuQty)
admin.site.register(FbaShipmentPaidBill)
admin.site.register(ReceivedSkuQty)
admin.site.register(NearestReceivablePurchasedQty)
admin.site.register(Upc)
admin.site.register(SkuUpc)
admin.site.register(Supplier)
admin.site.register(UserSupplier)
admin.site.register(SkuSupplier)
admin.site.register(SkuPurchasingPrice)
admin.site.register(SkuHeadShippingUnitCost)
admin.site.register(SkuAssetLiabilityTable)
admin.site.register(SkuManagedBySalesPerson)
admin.site.register(FbaShipmentCost)
admin.site.register(SkuPurchaseOrder)
admin.site.register(ProfitLossTable)
admin.site.register(CurrencyRate)
admin.site.register(ProductionStageTypeParameter)
admin.site.register(SkuProductionStageTypeParameter)
admin.site.register(DownloadedReport)
admin.site.register(PaymentTransactionDetail)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'new', 'image', 'discontinued', 'transparency')
    fields = ('sku', 'new', 'image', 'discontinued', 'transparency')


@admin.register(FulfillmentCenterCodeCountry)
class FulfillmentCenterCodeCountryAdmin(admin.ModelAdmin):
    list_display = ('country', 'code')


@admin.register(HistoryTodayProductSales)
class HistoryTodayProductSalesAdmin(admin.ModelAdmin):
    list_filter = (
        ('date', admin.DateFieldListFilter),
    )


@admin.register(HistoryTodaySales)
class HistoryTodaySalesAdmin(admin.ModelAdmin):
    list_filter = (
        ('date', admin.DateFieldListFilter),
    )


@admin.register(ProductionPlanProgress)
class ProductionPlanProgressAdmin(admin.ModelAdmin):
    list_display = [field.name for field in ProductionPlanProgress._meta.get_fields(
    ) if field.name not in ['production_stages']]
    fields = [field.name for field in ProductionPlanProgress._meta.get_fields(
    ) if field.name not in ['id']]

    # list_display = ('production_plan_number', 'sku', 'qty', 'deadline_date', 'ongoing')
    # fields = ('production_plan_number', 'sku', 'qty', 'deadline_date', 'ongoing')


@admin.register(ProductionStage)
class ProductionStageAdmin(admin.ModelAdmin):
    list_display = [field.name for field in ProductionStage._meta.get_fields() if field.name not in [
        'productionplanprogress', 'productionstagetypeparameter', 'skuproductionstagetypeparameter']]


@admin.register(DailyProductSalesAndInventory)
class DailyProductSalesAndInventoryAdmin(admin.ModelAdmin):
    search_fields = ('sku', 'asin')
    ordering = ['-date']
    list_display = [
        field.name for field in DailyProductSalesAndInventory._meta.get_fields()]


@admin.register(SkuFnSkuAsinCountry)
class SkuFnSkuAsinCountryAdmin(admin.ModelAdmin):
    search_fields = ('seller_sku', 'sku', 'asin', 'fnsku')
    list_display = [
        field.name for field in SkuFnSkuAsinCountry._meta.get_fields()]


@admin.register(AdPerformaceDaily)
class AdPerformaceDailyAdmin(admin.ModelAdmin):
    search_fields = ('date', 'country')
    list_display = ['country', 'date', 'cost', 'ad_sales']


@admin.register(ReceivedSkuQtyVJ)
class ReceivedSkuQtyVJAdmin(admin.ModelAdmin):
    search_fields = ('shipment_id', 'sku')
    list_display = ['shipment_id', 'sku', 'qty']


@admin.register(FbaShipmentVJ)
class FbaShipmentVJAdmin(admin.ModelAdmin):
    search_fields = ('shipment_id', 'shipment_name')
    list_display = ['shipment_id', 'shipment_name', 'country', 'closed']


@admin.register(ShippedProductSkuQty)
class ShippedProductSkuQtyAdmin(admin.ModelAdmin):
    search_fields = ('sku', )
    list_display = [field.name for field in ShippedProductSkuQty._meta.get_fields()]