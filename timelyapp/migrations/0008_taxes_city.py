# Generated by Django 3.2.9 on 2021-12-17 01:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0007_taxes'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxes',
            name='city',
            field=models.CharField(default='Berkeley', max_length=24),
        ),
    ]
