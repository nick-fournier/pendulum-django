# Generated by Django 3.2.4 on 2021-08-16 22:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timelyapp', '0012_alter_customuser_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='recent_pi',
            field=models.CharField(default=None, max_length=28, null=True),
        ),
    ]