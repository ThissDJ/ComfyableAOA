# Generated by Django 3.0.7 on 2020-06-08 13:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salesMonitor', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='image_height',
            field=models.PositiveIntegerField(blank=True, default='100', editable=False, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='image_width',
            field=models.PositiveIntegerField(blank=True, default='100', editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, help_text='Product Picture', null=True, upload_to='productimage', verbose_name='Product Picture'),
        ),
    ]
