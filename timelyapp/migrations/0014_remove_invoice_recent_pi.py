# Generated by Django 3.2.4 on 2021-08-16 23:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0013_invoice_recent_pi'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoice',
            name='recent_pi',
        ),
    ]