# Generated by Django 3.2.9 on 2022-01-07 21:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0003_auto_20220107_1236'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxes',
            name='compound',
            field=models.BooleanField(default=True),
        ),
    ]