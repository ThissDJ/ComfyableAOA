# Generated by Django 3.0.7 on 2021-01-12 08:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('salesMonitor', '0029_supplier'),
    ]

    operations = [
        migrations.CreateModel(
            name='SkuSupplier',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sku', models.CharField(default='', max_length=30)),
                ('supplier', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='salesMonitor.Supplier')),
            ],
        ),
    ]
