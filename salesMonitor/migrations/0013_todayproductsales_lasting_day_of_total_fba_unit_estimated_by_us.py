# Generated by Django 3.0.7 on 2020-06-20 15:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salesMonitor', '0012_todayproductsales_lasting_day_of_available_fc_estimated_by_us'),
    ]

    operations = [
        migrations.AddField(
            model_name='todayproductsales',
            name='lasting_day_of_total_fba_unit_estimated_by_us',
            field=models.FloatField(default=0),
        ),
    ]
