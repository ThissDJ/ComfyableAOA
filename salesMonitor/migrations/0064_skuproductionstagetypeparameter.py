# Generated by Django 3.0.7 on 2023-06-29 08:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salesMonitor', '0063_auto_20230629_0455'),
    ]

    operations = [
        migrations.CreateModel(
            name='SkuProductionStageTypeParameter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=30)),
                ('sku', models.CharField(default='', max_length=30)),
                ('production_stages', models.ManyToManyField(to='salesMonitor.ProductionStage')),
            ],
        ),
    ]
