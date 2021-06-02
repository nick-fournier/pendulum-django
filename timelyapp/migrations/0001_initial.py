# Generated by Django 3.2.3 on 2021-06-02 02:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('first_name', models.CharField(default=None, max_length=64)),
                ('last_name', models.CharField(default=None, max_length=64)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address_1', models.CharField(max_length=128, verbose_name='address')),
                ('address_2', models.CharField(blank=True, default=None, max_length=128, null=True, verbose_name="address cont'd")),
                ('city', models.CharField(default='Zanesville', max_length=64, verbose_name='city')),
                ('state', models.CharField(choices=[('AL', 'Alabama'), ('AZ', 'Arizona'), ('AR', 'Arkansas'), ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'), ('DC', 'District of Columbia'), ('FL', 'Florida'), ('GA', 'Georgia'), ('ID', 'Idaho'), ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'), ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'), ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'), ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'), ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'), ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'), ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'), ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'), ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'), ('WI', 'Wisconsin'), ('WY', 'Wyoming'), ('AK', 'Alaska'), ('HI', 'Hawaii'), ('AS', 'American Samoa'), ('GU', 'Guam'), ('MP', 'Northern Mariana Islands'), ('PR', 'Puerto Rico'), ('VI', 'Virgin Islands'), ('AA', 'Armed Forces Americas'), ('AE', 'Armed Forces Europe'), ('AP', 'Armed Forces Pacific'), ('FM', 'Federated States of Micronesia'), ('MH', 'Marshall Islands'), ('PW', 'Palau')], default='OH', max_length=36, null=True, verbose_name='state')),
                ('zip_code', models.CharField(default='43701', max_length=5, verbose_name='zip code')),
                ('country', models.CharField(default='USA', max_length=5, verbose_name='country')),
            ],
        ),
        migrations.CreateModel(
            name='Business',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_member', models.BooleanField(default=False)),
                ('business_name', models.CharField(default=None, max_length=64, unique=True)),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('phone', phonenumber_field.modelfields.PhoneNumberField(blank=True, default=None, max_length=128, null=True, region=None)),
                ('fax', phonenumber_field.modelfields.PhoneNumberField(blank=True, default=None, max_length=128, null=True, region=None)),
                ('date_joined', models.DateTimeField()),
                ('billing_address', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='billing_address', to='timelyapp.address')),
                ('managers', models.ManyToManyField(related_name='managers', to=settings.AUTH_USER_MODEL)),
                ('owner', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('shipping_address', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='shipping_address', to='timelyapp.address')),
            ],
        ),
        migrations.CreateModel(
            name='Discount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_code', models.CharField(default=None, max_length=100, null=True)),
                ('description', models.CharField(default=None, max_length=100, null=True)),
                ('discount_ratio', models.DecimalField(decimal_places=6, default=1.0, max_digits=10)),
                ('business', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='timelyapp.business')),
            ],
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_name', models.CharField(default=None, max_length=16, null=True)),
                ('date_sent', models.DateField(null=True)),
                ('date_due', models.DateField(null=True)),
                ('terms', models.CharField(choices=[('Custom', 'Custom due date'), ('COD', 'Cash on delivery'), ('CIA', 'Cash in advance'), ('NET7', 'Net 7 days'), ('NET10', 'Net 10 days'), ('NET30', 'Net 30 days'), ('NET60', 'Net 60 days'), ('NET90', 'Net 90 days'), ('NET120', 'Net 120 days')], default='NET30', max_length=24, null=True)),
                ('invoice_total_price', models.DecimalField(decimal_places=2, default=None, max_digits=12, null=True)),
                ('currency', models.CharField(default='USD', max_length=6, null=True)),
                ('notes', models.CharField(default='Thank you for your payment!', max_length=200, null=True)),
                ('is_flagged', models.BooleanField(default=False)),
                ('is_scheduled', models.BooleanField(default=False)),
                ('is_paid', models.BooleanField(default=False)),
                ('invoice_only', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Newsletter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('first_name', models.CharField(default=None, max_length=64, null=True)),
                ('last_name', models.CharField(default=None, max_length=64, null=True)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Payments',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('ACH', 'Bank transfer'), ('CHECK', 'Check'), ('CREDIT', 'Credit card'), ('LATER', 'Pay later with Timely'), ('FINANCE', 'Invoice financing with Timely')], default='ACH', max_length=64, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_name', models.CharField(default=None, max_length=100, null=True)),
                ('item_description', models.CharField(default=None, max_length=500, null=True)),
                ('quantity_purchased', models.DecimalField(decimal_places=6, max_digits=18)),
                ('item_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('item_total_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('discount_code', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='timelyapp.discount')),
                ('invoice', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='items', to='timelyapp.invoice')),
            ],
        ),
        migrations.AddField(
            model_name='invoice',
            name='accepted_payments',
            field=models.ManyToManyField(default=[1, 2, 3], related_name='accepted_payments', to='timelyapp.Payments'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='bill_from',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bill_from', to='timelyapp.business'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='bill_to',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bill_to', to='timelyapp.business'),
        ),
        migrations.CreateModel(
            name='Inventory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_updated', models.DateField(null=True)),
                ('item_name', models.CharField(default=None, max_length=100, null=True)),
                ('description', models.CharField(default=None, max_length=500, null=True)),
                ('quantity_in_stock', models.DecimalField(decimal_places=6, default=None, max_digits=18, null=True)),
                ('item_unit', models.CharField(default='ea', max_length=10, null=True)),
                ('item_price', models.DecimalField(decimal_places=2, default=None, max_digits=12, null=True)),
                ('currency', models.CharField(default='USD', max_length=6, null=True)),
                ('business', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='timelyapp.business')),
            ],
        ),
    ]
