# Generated by Django 3.2 on 2021-05-05 04:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0002_auto_20210504_2048'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventory',
            name='unit',
            field=models.CharField(default='ea', max_length=10, null=True),
        ),
    ]
