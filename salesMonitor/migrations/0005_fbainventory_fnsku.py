# Generated by Django 3.0.7 on 2020-06-09 12:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salesMonitor', '0004_fbainventory'),
    ]

    operations = [
        migrations.AddField(
            model_name='fbainventory',
            name='fnsku',
            field=models.CharField(default='nofnsku', max_length=30, unique=True),
        ),
    ]
