# Generated by Django 3.2 on 2021-05-05 03:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='unit',
        ),
        migrations.RemoveField(
            model_name='order',
            name='unit_price',
        ),
    ]