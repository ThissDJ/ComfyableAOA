# Generated by Django 3.0.7 on 2023-03-11 06:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salesMonitor', '0053_fbashipmentpaidbill'),
    ]

    operations = [
        migrations.AddField(
            model_name='fbashipmentpaidbill',
            name='weight_volumn_factor',
            field=models.IntegerField(default=6000),
        ),
    ]
