from django import template

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

@register.filter(name='check_shenzhen_inventory')
def check_shenzhen_inventory(sku):
    from salesMonitor.models import Inventory
    shenzhen_warehouse_name = '深圳A016'
    shenzhen_inventory = Inventory.objects.filter(sku = sku, warehouse_name = shenzhen_warehouse_name)
    if shenzhen_inventory.count():
        shenzhen_inventory = shenzhen_inventory.first().qty
    else:
        shenzhen_inventory = 0
    return shenzhen_inventory
