# Generated by Django 3.0.7 on 2023-06-30 16:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salesMonitor', '0064_skuproductionstagetypeparameter'),
    ]

    operations = [
        migrations.AddField(
            model_name='productionplanprogress',
            name='current_stage_name',
            field=models.CharField(default='', max_length=30),
        ),
    ]
