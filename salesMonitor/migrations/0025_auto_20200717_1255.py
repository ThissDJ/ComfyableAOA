# Generated by Django 3.0.7 on 2020-07-17 12:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salesMonitor', '0024_fbashipment_closed'),
    ]

    operations = [
        migrations.AddField(
            model_name='fbashipment',
            name='estimated_receiving_date',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='fbashipment',
            name='shipped_date',
            field=models.DateField(null=True),
        ),
    ]
