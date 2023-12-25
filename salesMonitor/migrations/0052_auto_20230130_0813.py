# Generated by Django 3.0.7 on 2023-01-30 08:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salesMonitor', '0051_remotefulfillmentsku'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='actual_weight_forced',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='product',
            name='package_height',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='product',
            name='package_length',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='product',
            name='package_weight',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='product',
            name='package_width',
            field=models.FloatField(default=0),
        ),
    ]
