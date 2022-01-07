# Generated by Django 3.2.9 on 2022-01-07 20:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0002_auto_20220107_1235'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='item_total_tax',
            new_name='item_tax_amt',
        ),
        migrations.AlterField(
            model_name='order',
            name='item_tax_rates',
            field=models.ManyToManyField(default=None, related_name='item_taxes', to='timelyapp.Taxes'),
        ),
    ]
