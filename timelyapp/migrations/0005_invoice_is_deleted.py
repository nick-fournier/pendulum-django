# Generated by Django 3.2.7 on 2021-10-19 16:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0004_alter_order_quantity_purchased'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
