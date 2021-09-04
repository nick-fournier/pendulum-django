# Generated by Django 3.2.4 on 2021-09-03 22:01

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0016_invoice_uuid'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoice',
            name='uuid',
        ),
        migrations.AlterField(
            model_name='invoice',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]
