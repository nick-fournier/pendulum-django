# Generated by Django 3.2.9 on 2022-01-14 03:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='item_description',
            field=models.CharField(blank=True, default=None, max_length=500, null=True),
        ),
    ]