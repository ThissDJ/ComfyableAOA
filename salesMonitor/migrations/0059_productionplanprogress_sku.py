# Generated by Django 3.0.7 on 2023-06-27 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salesMonitor', '0058_productionplanprogress'),
    ]

    operations = [
        migrations.AddField(
            model_name='productionplanprogress',
            name='sku',
            field=models.CharField(default='', max_length=30),
        ),
    ]
