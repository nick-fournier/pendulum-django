
from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone
# from address.models import AddressField
from phonenumber_field.modelfields import PhoneNumberField

#from shortuuidfield import ShortUUIDField
from customshortuuidfield import CustomShortUUIDField
import shortuuid

# Address stuff
# from django.contrib.gis.db import models
from django.utils.translation import ugettext as _
# from django.contrib.localflavor.us.models import USStateField

from django_countries.fields import CountryField


# Token Auth
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

# Stripe
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Custom User
from .managers import CustomUserManager
from .choices import *
import datetime

# Automatically generates token for each user
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

def xadr(s1, s2):
    return s1 + '' if s2 is None else str(s2)

class Address(models.Model):
    address_1 = models.CharField(_("address"), max_length=128)
    address_2 = models.CharField(_("address cont'd"), null=True, default=None, max_length=128, blank=True)
    city = models.CharField(_("city"), max_length=64, default="Zanesville")
    state = models.CharField(_("state"), default="OH", null=True, max_length=36, choices=STATES_CHOICES)
    zip_code = models.CharField(_("zip code"), max_length=5, default="43701")
    country = models.CharField(_("country"), max_length=5, default="USA")

    def __str__(self):
        return "%s, %s, %s %s, %s" %(xadr(self.address_1, self.address_2),
                                     self.city,
                                     self.state,
                                     self.zip_code,
                                     self.country
                                     )


class Business(models.Model):
    id = CustomShortUUIDField(primary_key=True, prefix="biz_")
    is_member = models.BooleanField(default=False)
    is_individual = models.BooleanField(default=False)
    stripe_act_id = models.CharField(default=None, null=True, blank=True, max_length=255, unique=True)
    stripe_cus_id = models.CharField(default=None, null=True, blank=True, max_length=255, unique=True)
    #owner = models.ForeignKey(CustomUser, default=None, null=True, on_delete=models.CASCADE)
    #managers = models.ManyToManyField(CustomUser, default=None, related_name='managers')
    business_name = models.CharField(default=None, max_length=64, unique=True)
    business_email = models.EmailField(_('email address'), unique=True)
    business_phone = PhoneNumberField(default=None, blank=True, null=True)
    business_fax = PhoneNumberField(default=None, blank=True, null=True)
    billing_address = models.ForeignKey(Address, default=None, null=True, on_delete=models.CASCADE, related_name='billing_address')
    shipping_address = models.ForeignKey(Address, default=None, null=True, on_delete=models.CASCADE, related_name='shipping_address')
    date_joined = models.DateTimeField()

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.date_joined = timezone.now()
        return super(Business, self).save(*args, **kwargs)

    def __str__(self):
        return "%s" %(self.business_name)

# Create your models here.
class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    id = CustomShortUUIDField(primary_key=True, prefix="usr_")
    business = models.ForeignKey(Business, default=None, null=True, on_delete=models.CASCADE, related_name='business_user')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()
    first_name = models.CharField(default=None, max_length=64)
    last_name = models.CharField(default=None, max_length=64)
    role = models.CharField(default='OWNER', null=True, max_length=64, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.email


class Payments(models.Model):
    type = models.CharField(default='ACH', null=True, max_length=64, choices=PAYMENT_CHOICES)

    def __str__(self):
        return u"%s [%s]" % (self.get_type_display(), self.type)


class Discount(models.Model):
    business = models.ForeignKey(Business, default=None, null=True, on_delete=models.CASCADE)
    discount_code = models.CharField(default=None, null=True, max_length=100)
    description = models.CharField(default=None, null=True, max_length=100)
    discount_ratio = models.DecimalField(default=1.0, max_digits=10, decimal_places=6)

    def __str__(self):
        return "%s" %(self.description)

class Inventory(models.Model):
    id = CustomShortUUIDField(primary_key=True, prefix="itm_")
    business = models.ForeignKey(Business, default=None, null=True, on_delete=models.CASCADE)
    last_updated = models.DateField(null=True)
    item_name = models.CharField(default=None, null=True, max_length=100)
    description = models.CharField(default=None, null=True, max_length=500)
    quantity_in_stock = models.DecimalField(default=None, null=True, max_digits=18, decimal_places=6)
    item_unit = models.CharField(default='ea', null=True, max_length=10)
    unit_price = models.DecimalField(default=None, null=True, max_digits=12, decimal_places=2)
    currency = models.CharField(default='USD', null=True, max_length=6)

    def save(self, *args, **kwargs):
        self.last_updated = timezone.now()
        return super(Inventory, self).save(*args, **kwargs)

    def __str__(self):
        return "%s" %(self.name)

class Taxes(models.Model):
    id = CustomShortUUIDField(primary_key=True, prefix="tax_")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='tax_rate')
    percentage = models.DecimalField(default=0, max_digits=12, decimal_places=6)
    display_name = models.CharField(default=None, null=True, max_length=24)
    description = models.CharField(default=None, null=True, max_length=128)
    abbreviation = models.CharField(default=None, null=True, max_length=3)
    zipcode = models.CharField(default=None, null=True, max_length=10)
    city = models.CharField(default=None, null=True, max_length=24)
    state = models.CharField(default=None, null=True, max_length=24, choices=STATES_CHOICES)
    country = CountryField(blank_label='(select country)', default='US')
    compound = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_on = models.DateTimeField(default=None, null=True)

    def save(self):
        if self.is_deleted==True:
            self.deleted_on = datetime.datetime.now()
        super(Taxes, self).save()


class Invoice(models.Model):
    id = CustomShortUUIDField(primary_key=True, prefix="inv_")
    invoice_name = models.CharField(default=None, null=True, max_length=16)
    date_purchase = models.DateField(null=True)
    date_sent = models.DateField(null=True)
    date_due = models.DateField(null=True)
    date_paid = models.DateField(null=True)
    bill_from = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='bill_from')
    bill_to = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='bill_to')
    terms = models.CharField(default='NET30', null=True, max_length=24, choices=TERM_CHOICES)
    accepted_payments = models.ManyToManyField(Payments, default=[1, 2, 3], related_name='accepted_payments')
    invoice_tax_amt = models.DecimalField(default=0, null=True, max_digits=12, decimal_places=2)
    invoice_price = models.DecimalField(default=None, null=True, max_digits=12, decimal_places=2)
    invoice_total_price = models.DecimalField(default=None, null=True, max_digits=12, decimal_places=2)
    currency = models.CharField(default='USD', null=True, max_length=6)
    notes = models.CharField(default='Thank you for your payment!', null=True, max_length=200)
    is_flagged = models.BooleanField(default=False)
    is_scheduled = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_on = models.DateTimeField(default=None, null=True)
    invoice_only = models.BooleanField(default=False)
    #
    # def __str__(self):
    #     return "%s, $%s, due: %s" %(self.invoice_name,
    #                                 self.invoice_total_price,
    #                                 self.date_due)

    def save(self):
        if self.is_deleted==True:
            self.deleted_on = datetime.datetime.now()
        super(Invoice, self).save()


class Order(models.Model):
    id = CustomShortUUIDField(primary_key=True, prefix="ord_")
    invoice = models.ForeignKey(Invoice, null=True, on_delete=models.CASCADE, related_name='items')
    discount_code = models.ForeignKey(Discount, default=1, on_delete=models.CASCADE)
    item_name = models.CharField(default=None, null=True, max_length=100)
    item_description = models.CharField(default=None, null=True, blank=True, max_length=500)
    #quantity_purchased = models.DecimalField(max_digits=18, decimal_places=6)
    quantity_purchased = models.IntegerField()
    unit_price = models.DecimalField(default=None, null=True, max_digits=12, decimal_places=2)
    item_price = models.DecimalField(default=None, null=True, max_digits=12, decimal_places=2)
    item_total_price = models.DecimalField(max_digits=12, null=True, decimal_places=2)
    item_tax_rates = models.ManyToManyField(Taxes, default=None, related_name='item_taxes')
    item_tax_amt = models.DecimalField(default=0, null=True, max_digits=12, decimal_places=2)

class Outreach(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(default=None, null=True, max_length=64)
    business_name = models.CharField(default=None, null=True, max_length=64)
    employees = models.CharField(default=None, null=True, max_length=24, choices=EMPLOYEES_CHOICES)
    role = models.CharField(default=None, null=True, max_length=24, choices=QROLE_CHOICES)
    date_joined = models.DateTimeField(default=timezone.now)
    # key = models.CharField(default="p!OOR&E[WnxP(o6?p~m$AOi1d]Gc_`", null=False, max_length=64)

class FinancingRequests(models.Model):
    id = CustomShortUUIDField(primary_key=True, prefix="fin_")
    request_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='financing_user')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='financing_biz')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='financing_invoice')
    financing_type = models.CharField(default=None, max_length=24, choices=[('PAYOUT', 'Immediate Payment'),
                                                                            ('PAYLATER', 'Buy now pay later')])

