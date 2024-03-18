import datetime
import math
from django.db import models
from django.db.models import Sum
from PIL import Image
from django.contrib.auth.models import User
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


class DailySalesLastYear(models.Model):
    day = models.IntegerField(default=1)
    month = models.IntegerField(default=1)
    sales = models.FloatField()


class HistoryTodaySales(models.Model):
    date = models.DateField(null=False, blank=False)
    sales_today = models.FloatField()
    sales_same_day_last_year = models.FloatField()
    sales_month_to_date = models.FloatField(default=0)
    monthly_increase_on_sales = models.FloatField(default=0)
    ad_cost = models.FloatField()
    acos = models.FloatField()
    ad_cost_on_sales = models.FloatField()
    country = models.CharField(max_length=2,default='US')


class Product(models.Model):
    sku = models.CharField(max_length=30)
    new = models.BooleanField(default=False)
    discontinued = models.BooleanField(default=False)
    name_in_chinese = models.CharField(max_length=150, default="")
    transparency = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='productimage',
        null=True,
        blank=True,
        editable=True,
        help_text="Product Picture",
        verbose_name="Product Picture"
    )
    image_height = models.PositiveIntegerField(null=True, blank=True, editable=False, default="100")
    image_width = models.PositiveIntegerField(null=True, blank=True, editable=False, default="100")
    package_length = models.FloatField(default=0)
    package_width = models.FloatField(default=0)
    package_height = models.FloatField(default=0)
    package_weight = models.PositiveIntegerField(default=0)
    actual_weight_forced = models.BooleanField(default=False)

    def __unicode__(self):
        return "{0}".format(self.image)

    def save(self, *args, **kwargs):
        super(Product, self).save(*args, **kwargs)
        if not self.image:
            return
        image = Image.open(self.image)
        (width, height) = image.size
        width_height_ratio = float(width) / float(height)
        if width > height:
            new_width = min([100, width])
            new_height = new_width / width_height_ratio
        else:
            new_height = min([100, height])
            new_width = new_height * width_height_ratio
        size = (int(new_width), int(new_height))
        image = image.resize(size, Image.ANTIALIAS)
        image.save(self.image.path)

    def __str__(self):
        return self.sku


class FbaInventory(models.Model):
    sku = models.CharField(max_length=30, unique=False)
    fnsku = models.CharField(max_length=30, unique=False, default='nofnsku')
    asin = models.CharField(max_length=30)
    total_unit = models.IntegerField(default=0)
    available = models.IntegerField(default=0)
    inbound_fc_unit = models.IntegerField(default=0)
    fc_unit = models.IntegerField(default=0)
    inbound_unit = models.IntegerField(default=0)
    days_of_supply = models.IntegerField(default=0)
    recommended_replenishment_qty = models.IntegerField(default=0)
    recommended_ship_date = models.CharField(default="", max_length=15)
    country = models.CharField(max_length=2, default='US')

    def __str__(self):
        return '%s : %i: %i: %i' % (self.sku, self.available, self.fc_unit, self.inbound_unit)


class RemoteFulfillmentSku(models.Model):
    sku = models.CharField(max_length=30, unique=False)
    country = models.CharField(max_length=2, default='CA')

    def __str__(self):
        return '%s : %s' % (self.sku, self.country)


class TodayProductSales(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    sold_qty = models.IntegerField(default=0)
    sales_amount = models.FloatField(default=0)
    sold_qty_average_7d = models.FloatField(default=0)
    average_price_7d = models.FloatField(default=0)
    fba_inventory = models.ForeignKey(FbaInventory, on_delete=models.CASCADE, null=1)
    lasting_day_estimated_by_us = models.FloatField(default=0)
    lasting_day_of_available_estimated_by_us = models.FloatField(default=0)
    lasting_day_of_available_fc_estimated_by_us = models.FloatField(default=0)
    lasting_day_of_total_fba_unit_estimated_by_us = models.FloatField(default=0)
    country = models.CharField(max_length=2, default='US')

    def save(self, *args, **kwargs):
        if self.fba_inventory is not None:
            self.lasting_day_of_available_estimated_by_us = self.fba_inventory.available / self.sold_qty_average_7d
            self.lasting_day_of_available_fc_estimated_by_us = (self.fba_inventory.available + self.fba_inventory.fc_unit) / self.sold_qty_average_7d
            # if self.product.new:
            #     self.lasting_day_of_total_fba_unit_estimated_by_us = self.fba_inventory.total_unit / (self.sold_qty_average_7d * 1.5)
            #     if self.fba_inventory.total_unit / (self.sold_qty_average_7d * 1.5) < self.fba_inventory.available / self.sold_qty_average_7d:
            #         self.lasting_day_of_total_fba_unit_estimated_by_us = self.fba_inventory.available / self.sold_qty_average_7d
            # else:
            #     self.lasting_day_of_total_fba_unit_estimated_by_us = self.fba_inventory.total_unit / self.sold_qty_average_7d
            self.lasting_day_of_total_fba_unit_estimated_by_us = self.fba_inventory.total_unit / self.sold_qty_average_7d
            super(TodayProductSales, self).save(*args, **kwargs)
        else:
            super(TodayProductSales, self).save(*args, **kwargs)

    def __str__(self):
        return self.product.sku


class Last7dayProductSales(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    sold_qty = models.IntegerField(default=0)
    sales_amount = models.FloatField()
    sold_qty_average_7d = models.FloatField()
    average_price_7d = models.FloatField()
    country = models.CharField(max_length=2, default='US')


class ReceivablePurchasedQty(models.Model):
    sku = models.CharField(max_length=30, unique=True)
    qty = models.IntegerField(default=0)

    def __str__(self):
        return '%s : %i' % (self.sku, self.qty)


class NearestReceivablePurchasedQty(models.Model):
    sku = models.CharField(max_length=30, unique=True)
    qty = models.IntegerField(default=0)
    date = models.DateField(null=True)

    def __str__(self):
        return '%s : %i' % (self.sku, self.qty)


class HistoryLast7dayProductSales(models.Model):
    date = models.DateField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    sold_qty = models.IntegerField(default=0)
    sales_amount = models.FloatField()
    sold_qty_average_7d = models.FloatField()
    average_price_7d = models.FloatField()
    country = models.CharField(max_length=2, default='US')


class HistoryTodayProductSales(models.Model):
    date = models.DateField(null=False, blank=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    sold_qty = models.IntegerField(default=0)
    sales_amount = models.FloatField(default=0)
    sold_qty_average_7d = models.FloatField(default=0)
    average_price_7d = models.FloatField(default=0)
    fba_inventory = models.ForeignKey(FbaInventory, on_delete=models.CASCADE, null=1)
    lasting_day_estimated_by_us = models.FloatField(default=0)
    lasting_day_of_available_estimated_by_us = models.FloatField(default=0)
    lasting_day_of_available_fc_estimated_by_us = models.FloatField(default=0)
    lasting_day_of_total_fba_unit_estimated_by_us = models.FloatField(default=0)
    country = models.CharField(max_length=2, default='US')

    def save(self, *args, **kwargs):
        if self.fba_inventory is not None:
            self.lasting_day_of_available_estimated_by_us = self.fba_inventory.available / self.sold_qty_average_7d
            self.lasting_day_of_available_fc_estimated_by_us = (self.fba_inventory.available + self.fba_inventory.fc_unit) / self.sold_qty_average_7d
            # if self.product.new:
            #     self.lasting_day_of_total_fba_unit_estimated_by_us = self.fba_inventory.total_unit / (self.sold_qty_average_7d * 1.5)
            #     if self.fba_inventory.total_unit / (self.sold_qty_average_7d * 1.5) < self.fba_inventory.available / self.sold_qty_average_7d:
            #         self.lasting_day_of_total_fba_unit_estimated_by_us = self.fba_inventory.available / self.sold_qty_average_7d
            # else:
            #     self.lasting_day_of_total_fba_unit_estimated_by_us = self.fba_inventory.total_unit / self.sold_qty_average_7d
            self.lasting_day_of_total_fba_unit_estimated_by_us = self.fba_inventory.total_unit / self.sold_qty_average_7d
            super(HistoryTodayProductSales, self).save(*args, **kwargs)

    def __str__(self):
        return self.product.sku


class CurrencyRate(models.Model):
    from_country = models.CharField(max_length=2, unique=False)
    to_country = models.CharField(max_length=2, unique=False)
    rate = models.FloatField(default=0)
    date = models.DateField(null=False, blank=False, default=datetime.date.today)


class ShippedSkuQty(models.Model):
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING)
    sku = models.CharField(max_length=30, unique=False, default="")
    qty = models.IntegerField(default=0)
    shipped_date = models.DateField(null=True)
    estimated_receiving_date = models.DateField(null=True)

    def __str__(self):
        return '%s : %i' % (self.sku, self.qty)


class FulfillmentCenterCodeCountry(models.Model):
    code = models.CharField(max_length=15, unique=True)
    country = models.CharField(max_length=2, default='US')


class FbaShipment(models.Model):
    shipment_id = models.CharField(max_length=15, unique=True)
    shipment_name = models.CharField(max_length=50, unique=True)
    country = models.CharField(max_length=2, unique=False, default="US")
    fc_code = models.CharField(max_length=15, default="")
    shipped_sku_qties = models.ManyToManyField(ShippedSkuQty)
    shipped_date = models.DateField(null=True)
    estimated_receiving_date = models.DateField(null=True)
    closed = models.BooleanField(default=False)

    def __str__(self):
        return '%s' % (self.shipment_id)


class FbaShipmentPaidBill(models.Model):
    shipment_id = models.CharField(max_length=15, unique=True)
    paid_amount = models.FloatField(default=0)
    weight = models.IntegerField(default=0)
    weight_volumn_factor = models.IntegerField(default=6000)

    def __str__(self):
        return '%s' % (self.shipment_id)


class ProductInventoryUnitValue(models.Model):
    sku = models.CharField(max_length=30, unique=False, default="")
    inventory_value = models.FloatField(default=0)
    date = models.DateField(null=True)
    additional_cost = models.FloatField(default=0)

    def __str__(self):
        return '%s: %.1f' % (self.sku, self.inventory_value)

    def inventory_value_plus_additional_cost(self):
        return self.inventory_value + self.additional_cost


class ReceivedSkuQty(models.Model):
    shipment_id = models.CharField(max_length=15, unique=False)
    sku = models.CharField(max_length=30, unique=False, default="")
    qty = models.IntegerField(default=0)

    def __str__(self):
        return '%s : %i : %s' % (self.sku, self.qty, self.shipment_id)


class Inventory(models.Model):
    warehouse_name = models.CharField(max_length=15, unique=False)
    sku = models.CharField(max_length=30, unique=False, default="")
    qty = models.IntegerField(default=0)

    def __str__(self):
        return '%s : %i' % (self.sku, self.qty)


class Upc(models.Model):
    upc = models.CharField(max_length=30, unique=True, default="")
    used = models.BooleanField(default=False)


class SkuUpc(models.Model):
    sku = models.CharField(max_length=30, unique=False, default="")
    upc = models.ForeignKey(Upc, on_delete=models.DO_NOTHING, null=True)

    def __str__(self):
        if self.upc:
            return '%s : %s' % (self.sku, self.upc.upc)
        else:
            return '%s' % (self.sku)


class Supplier(models.Model):
    name = models.CharField(max_length=60, unique=False, default="")

    def __str__(self):
        return self.name


class UserSupplier(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True)
    supplier_id = models.CharField(max_length=60, unique=False, default="GYS001")

    def __str__(self):
        return '%s : %s' % (self.user.username, self.supplier_id)


class SkuSupplier(models.Model):
    sku = models.CharField(max_length=30, unique=False, default="")
    supplier_id = models.CharField(max_length=60, unique=False, default="GYS001")

    def __str__(self):
        return '%s : %s' % (self.sku, self.supplier_id)


class SkuPurchasingPrice(models.Model):
    sku = models.CharField(max_length=30, unique=False, default="")
    purchasing_price = models.FloatField()
    date = models.DateField(null=False, blank=False)

    def __str__(self):
        return '%s : ¥%s, %s' % (self.sku, self.purchasing_price, self.date.strftime('%Y-%m-%d'))


class SkuHeadShippingUnitCost(models.Model):
    TYPES = (
        ('S', 'Sea'),
        ('A', 'Air'),
        ('G', 'General'),
    )
    sku = models.CharField(max_length=30, unique=False, default="")
    type = models.CharField(max_length=1, choices=TYPES)
    country = models.CharField(max_length=2)
    head_shipping_unit_cost = models.FloatField()
    date = models.DateField(null=False, blank=False)

    def __str__(self):
        return '%s : ¥%s,%s,%s' % (self.sku, self.head_shipping_unit_cost, self.country, self.date.strftime('%Y-%m-%d'))


class SkuAssetLiabilityTable(models.Model):
    sku = models.CharField(max_length=30, unique=False, default="")
    for_sales = models.BooleanField(default=False)
    liabilities = models.FloatField(default=0.0)
    date = models.DateField(null=False, blank=False)
    initial_inventory_quantity = models.IntegerField(default=0)
    unit_purchasing_price = models.FloatField(default=0.0)
    initial_inventory_value = models.FloatField(default=0.0)
    head_shipping_unit_price = models.FloatField(default=0.0)
    initial_other_cost = models.FloatField(default=0.0)
    initial_liabilities = models.FloatField(default=0.0)
    initial = models.BooleanField(default=False)
    initial_investment = models.FloatField(default=0.0)
    history_inventment = models.FloatField(default=0.0)
    cash_amount = models.FloatField(default=0.0)
    net_asset_amount = models.FloatField(default=0.0)
    previous_asset_liability_table_id = models.IntegerField(default=0)


class SkuManagedBySalesPerson(models.Model):
    sku = models.CharField(max_length=30, unique=False, default="")
    sales_person_name = models.CharField(max_length=30, unique=False, default="")
    sales_assistant_name = models.CharField(max_length=30, unique=False, default="lijunjie")


class SkuContributor(models.Model):
    sku = models.CharField(max_length=30, unique=False, default="")
    proposer_name = models.CharField(max_length=30, unique=False, default="lijunjie")
    designer_name = models.CharField(max_length=30, unique=False, default="lijunjie")


class SkuWeight(models.Model):
    sku = models.CharField(max_length=30, unique=False, default="")
    heavy_or_light = models.BooleanField(default=False)
    real_weight = models.FloatField(default=0.25)
    converted_weight = models.FloatField(default=0.3)


class FbaShipmentCost(models.Model):
    SHIPWAYS = (
        ('S', '海派'),
        ('A', '空派'),
        ('E', '快递'),
    )
    shipment_id = models.CharField(max_length=15)
    shipway = models.CharField(max_length=1, choices=SHIPWAYS)
    cost_per_kg = models.FloatField(default=45.0)
    date = models.DateField(null=False, blank=False)


class SkuPurchaseOrder(models.Model):
    sku = models.CharField(max_length=30, unique=False, default="")
    po_number = models.CharField(max_length=30, unique=False, default="")
    qty = models.IntegerField(default=0)
    transaction_amount = models.FloatField(default=0.0)
    date = models.DateField(null=False, blank=False)

    def __str__(self):
        return '%s : %s' % (self.sku, self.date.strftime('%Y-%m-%d'))
    

class ProfitLossTable(models.Model):
    STATUS = (
        ('T', '交易订单录入'),
        ('P', '购货和头程运费确认'),
        ('F', '各种费用扣除'),
        ('S', '股东分红扣除'),
    )
    COUNTRIES = (('US', 'US'), ('CA', 'CA'), ('AU', 'AU'), ('AE', 'AE'), ('UK', 'UK'),
                 ('DE', 'DE'), ('FR', 'FR'), ('IT', 'IT'), ('ES', 'ES'), ('SG', 'SG'))
    sku = models.CharField(max_length=30, unique=False, default="")
    status = models.CharField(max_length=1, choices=STATUS)
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    sales_amount = models.FloatField(default=0.0)
    sales_quantity = models.IntegerField(default=0)
    product_purchasing_fee = models.FloatField(default=0.0)
    head_shipping_fee = models.FloatField(default=0.0)
    amazon_fee = models.FloatField(default=0.0)
    ad_fee = models.FloatField(default=0.0)
    sales_person = models.CharField(max_length=30, unique=False, default="lijunjie")
    sales_person_bonus_fee = models.FloatField(default=0.0)
    sales_person_bonus_fee_percent = models.FloatField(default=0.05)
    product_originator_bonus_fee = models.FloatField(default=0.0)
    product_originator_bonus_fee_percent = models.FloatField(default=0.05)
    product_designer_bonus_fee = models.FloatField(default=0.0)
    product_designer_bonus_fee_percent = models.FloatField(default=0.05)
    platform_fee = models.FloatField(default=0.0)
    platform_fee_percent = models.FloatField(default=0.05)
    other_fee = models.FloatField(default=0.0)
    shareholder_bonus_fee = models.FloatField(default=0.0)
    country = models.CharField(max_length=2, choices=COUNTRIES)
    currency_rate = models.FloatField(default=6.5)
    profit_before_deduct_bonus = models.FloatField(default=0.0)
    profit_after_deduct_bounus = models.FloatField(default=0.0)

    def __str__(self):
        return '%s : %s : %s' % (self.sku, self.start_date.strftime('%Y-%m-%d'), self.end_date.strftime('%Y-%m-%d'))


class ProductionStage(models.Model):
    name = models.CharField(max_length=30, default="")
    production_stage_type_name = models.CharField(max_length=30, default="")
    minimum_days = models.IntegerField(null=True, blank=True)
    duration_days = models.IntegerField(default=0)
    daily_production_units = models.IntegerField(null=True, blank=True)
    start_date_estimated = models.DateField(null=True, blank=True)
    start_date_actually = models.DateField(null=True, blank=True)
    order_number = models.IntegerField(default=1)

    def __str__(self):
        return '%i. %s' % (self.order_number, self.name)


class ProductionPlanProgress(models.Model):
    production_plan_number = models.CharField(max_length=30, unique=True, default="")
    sku = models.CharField(max_length=30, default="")
    qty = models.IntegerField(default=0)
    manufacturer_number = models.CharField(max_length=40, default="")
    subcontractor_name = models.CharField(max_length=40, default="")
    deadline_date = models.DateField()
    ongoing = models.BooleanField(default=True)
    production_stages = models.ManyToManyField(ProductionStage)
    soonest_finishing_date = models.DateField(null=True, blank=True)
    current_stage_id = models.IntegerField(null=True, blank=True)
    current_stage_name = models.CharField(max_length=30, default="")

    def __str__(self):
        return self.production_plan_number

    def save(self, *args, **kwargs):
        if self.current_stage_id is not None and ProductionStage.objects.filter(id=self.current_stage_id).count():
            self.current_stage_name = ProductionStage.objects.get(id=self.current_stage_id).name
        else:
            self.current_stage_name = ""
        if self.id is not None:
            for production_stage in self.production_stages.all():
                if production_stage.daily_production_units is not None and self.qty != 0 and production_stage.minimum_days == None:
                    duration_days = math.ceil(float(self.qty) / float(production_stage.daily_production_units))
                    production_stage.duration_days = duration_days
                    production_stage.save()
                elif production_stage.daily_production_units is not None and self.qty != 0 and production_stage.minimum_days is not None:
                    duration_days = production_stage.minimum_days + max([0, math.ceil(float(self.qty - production_stage.daily_production_units) / float(production_stage.daily_production_units))])
                    production_stage.duration_days = duration_days
                    production_stage.save()
            if self.production_stages.count():
                left_days = self.production_stages.aggregate(Sum('duration_days'))['duration_days__sum']
                use_current_production_stage = True
                if self.current_stage_id is not None and ProductionStage.objects.filter(id=self.current_stage_id).count():
                    current_production_stage = ProductionStage.objects.get(id=self.current_stage_id)
                    # 判断是当前工序后序工序是否存在预计开始时间，如果有，则给予有预计开始时间的工序开始推断
                    next_estimated_production_stage = self.production_stages.filter(order_number__gt=current_production_stage.order_number, start_date_estimated__isnull=False)
                    if next_estimated_production_stage.count():
                        next_estimated_production_stage = next_estimated_production_stage.order_by('-order_number').first()
                        if next_estimated_production_stage.start_date_estimated > datetime.date.today():
                            self.soonest_finishing_date = next_estimated_production_stage.start_date_estimated + datetime.timedelta(days=self.production_stages.filter(order_number__gte = next_estimated_production_stage.order_number).aggregate(Sum('duration_days'))['duration_days__sum'])
                            use_current_production_stage = False
                    if use_current_production_stage:
                        left_days_of_current_production_stage = (datetime.date.today() - current_production_stage.start_date_actually).days
                        if left_days_of_current_production_stage >= current_production_stage.duration_days:
                            left_days_of_current_production_stage = 0
                        else:
                            left_days_of_current_production_stage = (current_production_stage.duration_days - left_days_of_current_production_stage)
                        left_days = left_days_of_current_production_stage
                        for production_stage in self.production_stages.filter(order_number__gt=current_production_stage.order_number):
                            left_days += production_stage.duration_days
                if use_current_production_stage:
                    self.soonest_finishing_date = datetime.date.today() + datetime.timedelta(days=left_days)
        super(ProductionPlanProgress, self).save(*args, **kwargs)

    @property
    def is_a_parent_production_plan(self):
        if (not self.subcontractor_name) and ProductionPlanProgress.objects.filter(production_plan_number__startswith=self.production_plan_number).count() > 1:
            return True
        return False

    @property
    def sewing_days(self):
        sewing_step = self.production_stages.all().filter(name='车缝')
        if sewing_step.count():
            sewing_step = sewing_step.first()
            return sewing_step.duration_days
        return 1

    @property
    def sewing_has_an_expected_date(self):
        sewing_step = self.production_stages.all().filter(name='车缝')
        if sewing_step.count():
            sewing_step = sewing_step.first()
            if sewing_step.start_date_estimated:
                return True
        return False

    @property
    def sewing_expected_date(self):
        sewing_step = self.production_stages.all().filter(name='车缝')
        if sewing_step.count():
            sewing_step = sewing_step.first()
            if sewing_step.start_date_estimated:
                return sewing_step.start_date_estimated
        return False

    @property
    def sewing_expected_date_fullcalendar(self):
        sewing_step = self.production_stages.all().filter(name='车缝')
        if sewing_step.count():
            sewing_step = sewing_step.first()
            if sewing_step.start_date_estimated:
                return (sewing_step.start_date_estimated).strftime('%Y-%m-%d')
        return False

    @property
    def sewing_expected_end_date_fullcalendar(self):
        sewing_step = self.production_stages.all().filter(name='车缝')
        if sewing_step.count():
            sewing_step = sewing_step.first()
            if sewing_step.start_date_estimated:
                return (sewing_step.start_date_estimated + datetime.timedelta(days=sewing_step.duration_days)).strftime('%Y-%m-%d')
        return False

    @property
    def status_color_fullcalendar(self):
        colorConfig = {'hasBoughtMaterial':
                       {'backgroundColor': 'yellow',
                        'textColor': 'black'
                        },
                       'hasCutMaterial':
                       {'backgroundColor': 'green',
                        'textColor': 'white'
                        },
                       'hasStartedSewing':
                       {'backgroundColor': 'pink',
                        'textColor': 'purple'
                        },
                       'default':
                       {'backgroundColor': 'blue',
                        'textColor': 'white'
                        },
                       }
        
        class FullcalendarEventColor:
            def __init__(self, backgroundColor, textColor):
                self.backgroundColor = backgroundColor
                self.textColor = textColor
        material_purchase_step = self.production_stages.all().get(name='买料')
        material_cut_step = self.production_stages.all().get(name__startswith='开料')
        sewing_step = self.production_stages.all().get(name='车缝')
        if sewing_step.start_date_actually:
            fullcalendarEventColor = FullcalendarEventColor(
                backgroundColor=colorConfig['hasStartedSewing']['backgroundColor'],
                textColor=colorConfig['hasStartedSewing']['textColor']
            )
            return fullcalendarEventColor
        elif material_cut_step.start_date_actually:
            fullcalendarEventColor = FullcalendarEventColor(
                backgroundColor=colorConfig['hasCutMaterial']['backgroundColor'],
                textColor=colorConfig['hasCutMaterial']['textColor']
            )
            return fullcalendarEventColor
        elif material_purchase_step.start_date_actually:
            fullcalendarEventColor = FullcalendarEventColor(
                backgroundColor=colorConfig['hasBoughtMaterial']['backgroundColor'],
                textColor=colorConfig['hasBoughtMaterial']['textColor']
            )
            return fullcalendarEventColor
        fullcalendarEventColor = FullcalendarEventColor(
            backgroundColor=colorConfig['default']['backgroundColor'],
            textColor=colorConfig['default']['textColor']
        )
        return fullcalendarEventColor
    

class ProductionStageTypeParameter(models.Model):
    name = models.CharField(max_length=30, default="")
    production_stages = models.ManyToManyField(ProductionStage)

    def __str__(self):
        return self.name


class SkuProductionStageTypeParameter(models.Model):
    production_type_name = models.CharField(max_length=30, default="")
    sku = models.CharField(max_length=30, default="")
    production_stages = models.ManyToManyField(ProductionStage)

    def __str__(self):
        return '%s %s' % (self.sku, self.production_type_name)


class DownloadedReport(models.Model):
    created_at = models.DateField(null=False, auto_now_add=True, blank=False)
    updated_at = models.DateField(null=False, auto_now=True, blank=False)
    report_id = models.CharField(max_length=10)
    report_start_time = models.DateField(null=False, blank=False)
    report_end_time = models.DateField(null=False, blank=False)


class PaymentTransactionDetail(models.Model):
    created_at = models.DateField(null=False, auto_now_add=True, blank=False)
    updated_at = models.DateField(null=False, auto_now_add=True, blank=False)
    downloaded_file_id = models.ForeignKey(DownloadedReport, on_delete=models.CASCADE)
    date_time = models.DateTimeField(null=False, blank=False)
    settlement_id = models.CharField(max_length=20)
    type = models.CharField(max_length=30)
    order_id = models.CharField(max_length=20)
    sku = models.CharField(max_length=20)
    description = models.CharField(max_length=500)
    quantity = models.IntegerField(default=0)
    marketplace = models.CharField(max_length=20)
    fulfillment = models.CharField(max_length=20)
    order_city = models.CharField(max_length=20)
    order_state = models.CharField(max_length=20)
    order_postal = models.CharField(max_length=20)
    product_sales = models.FloatField(default=0)
    shipping_credits = models.FloatField(default=0)
    gift_wrap_credits = models.FloatField(default=0)
    promotional_rebates = models.FloatField(default=0)
    sales_tax_collected = models.FloatField(default=0)
    low_value_goods = models.FloatField(default=0)
    selling_fees = models.FloatField(default=0)
    fba_fees = models.FloatField(default=0)
    other_transaction_fees = models.FloatField(default=0)
    other = models.FloatField(default=0)
    total = models.FloatField(default=0)

    def save_to_database(self):
        self.save()


# Cronjob update today and yesterday's data. update every 30 minutes. As long as the total inventory of a sku on that day is greater than 0, this sku has to be saved in this model, even the sold qty on that day is 0
# Please combine all the European countries except for GB to be EU
# Please set the default currency of EU to be EUR, for other none-european countries, set defualt currency of them as Amazon's default local currency, such as GB to be GBP
# for some countries, such as AU, AE, SA, there might be not days_of_supply_by_amazon and recommended_replenishment_qty. For JP, EU and US, there should be these two values.
class DailyProductSalesAndInventory(models.Model):
    """日常产品销售和库存"""
    sku = models.CharField(max_length=30, default="", name='sku', verbose_name='商品的库存单位(SKU)')
    fnsku = models.CharField(max_length=30, unique=False, default='nofnsku', name='fnsku', verbose_name='配送网络库存单位(FNSKU)')
    sold_qty = models.IntegerField(default=0, name='sold_qty', verbose_name='已售出数量')
    sales_amount = models.FloatField(default=0, name='sales_amount', verbose_name='销售金额')
    sold_qty_average_7d = models.FloatField(default=0, name='sold_qty_average_7d', verbose_name='近7天的平均售出数量')
    average_price_7d = models.FloatField(default=0, name='average_price_7d', verbose_name='近7天的平均价格')
    date = models.DateField(null=True, name='date', verbose_name='日期，记录数据对应的具体日期')
    asin = models.CharField(max_length=30, name='asin', verbose_name='亚马逊标准识别编号(ASIN)')
    total_unit = models.IntegerField(default=0, name='total_unit', verbose_name='总库存单位数')
    available = models.IntegerField(default=0, name='available', verbose_name='可用库存')
    inbound_fc_unit = models.IntegerField(default=0, name='inbound_fc_unit', verbose_name='在途库存以及fc中转库存数量')
    fc_unit = models.IntegerField(default=0, name='fc_unit', verbose_name='配送中心的库存单位')
    inbound_unit = models.IntegerField(default=0, name='inbound_unit', verbose_name='在途库存')
    days_of_supply_by_amazon = models.CharField(max_length=8, default='0', name='days_of_supply_by_amazon', verbose_name='亚马逊提供的供货天数')
    recommended_replenishment_qty = models.CharField(max_length=8, default='0', name='recommended_replenishment_qty', verbose_name='推荐补货数量')
    currency = models.CharField(max_length=2, default='USD', name='currency', verbose_name='货币单位')
    country = models.CharField(max_length=2, default='US', name='country', verbose_name='国家代码')
    
    class Meta:
        unique_together = ("sku", "date", "country")
        

class SkuFnSkuAsinCountry(models.Model):
    """记录sku和seller_sku的关系"""
    seller_sku = models.CharField(max_length=32, default='', verbose_name='原始sku')
    sku = models.CharField(max_length=32, default='', verbose_name='转售sku')
    asin = models.CharField(max_length=32, default='')
    fnsku = models.CharField(max_length=32, default='')
    country = models.CharField(max_length=4, default='')

    class Meta:
        unique_together = ('seller_sku', 'sku', 'asin', 'fnsku', 'country')


# the shipped product in FBA shipment
# Update every 30 minutes
class ShippedProductSkuQty(models.Model):
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING)
    sku = models.CharField(max_length=30, unique=False, default="")
    qty = models.IntegerField(default=0)
    shipped_date = models.DateField(null=True)
    estimated_receiving_date = models.DateField(null=True)

    def __str__(self):
        return '%s : %i' % (self.sku, self.qty)


# FBA shipment. VJ version
# fc_code stands for fulfillment center code
# Update every 30 minutes
# if all the sku's unreceived qty is smaller than shipment_close_threshold, then set the shipment's closed to be True
# Threshold:
# US: 15
# Not US: 4
class FbaShipmentVJ(models.Model):
    shipment_id = models.CharField(max_length=15, unique=True)
    shipment_name = models.CharField(max_length=50, unique=True)
    country = models.CharField(max_length=2, unique=False, default="US")
    shipped_product_sku_qties = models.ManyToManyField(ShippedProductSkuQty)
    shipped_date = models.DateField(null=True)
    closed = models.BooleanField(default=False)

    def __str__(self):
        return '%s' % self.shipment_id
    

class ShippedReceivedSkuQty(models.Model):
    fba_shopment_vj = models.ForeignKey(FbaShipmentVJ, on_delete=models.DO_NOTHING)
    sku = models.CharField(max_length=30, unique=False, default="")
    shipped_qty = models.IntegerField(default=0)
    received_qty = models.IntegerField(default=0)
    unreceived_qty = models.IntegerField(default=0)
    country = models.CharField(max_length=2, unique=False, default="US")

    def __str__(self):
        return '%s : %i : %i : %i:  %s: %s' % (self.sku, self.shipped_qty, self.received_qty, self.unreceived_qty, self.fba_shopment_vj.shipment_id, self.country)

    # @property
    # def unreceived(self):
    #     return max(0, self.shipped_qty - self.received_qty)


# Please combine all the European countries except for GB to be EU
# Update every 2 hours
class AdPerformaceDaily(models.Model):
    cost = models.FloatField(default=0)
    ad_sales = models.FloatField(default=0)
    date = models.DateField(null=True)
    country = models.CharField(max_length=2, unique=False, default="US")

    @property
    def acos(self):
        if self.ad_sales > 0:
            return float(self.cost) / float(self.ad_sales)
        else:
            return 0.0
