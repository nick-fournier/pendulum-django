# Generated by Django 3.2.9 on 2022-01-11 22:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0006_auto_20220111_1439'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, default=None, max_digits=12, null=True),
        ),
    ]
