from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .managers import CustomUserManager

TERM_CHOICES = [
    ('COD', 'Cash on delivery'),
    ('CIA', 'Cash in advance'),
    ('NET7', 'Net 7 days'),
    ('NET10', 'Net 10 days'),
    ('NET30', 'Net 30 days'),
    ('NET60', 'Net 60 days'),
    ('NET90', 'Net 90 days'),
    ('NET120', 'Net 120 days'),
]

# Create your models here.
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('email address'), unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

class Business(models.Model):
    is_member = models.BooleanField(default=False)
    owner = models.ForeignKey(CustomUser, default=None, null=True, on_delete=models.CASCADE)
    managers = models.ManyToManyField(CustomUser, related_name='managers')
    business_name = models.CharField(default=None, max_length=64)
    address = models.CharField(default=None, max_length=64)
    date_joined = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "%s" %(self.business_name)

class Discount(models.Model):
    business = models.ForeignKey(Business, default=None, null=True, on_delete=models.CASCADE)
    discount_code = models.CharField(default=None, null=True, max_length=100)
    description = models.CharField(default=None, null=True, max_length=100)
    discount_ratio = models.DecimalField(default=1.0, max_digits=10, decimal_places=6)

    def __str__(self):
        return "%s" %(self.description)

class Inventory(models.Model):
    business = models.ForeignKey(Business, default=None, null=True, on_delete=models.CASCADE)
    last_updated = models.DateField(null=True)
    description = models.CharField(default=None, null=True, max_length=100)
    quantity_in_stock = models.DecimalField(default=None, max_digits=10, decimal_places=6)
    unit = models.CharField(default='pc', null=True, max_length=3)
    unit_price = models.DecimalField(default=None, null=True, max_digits=10, decimal_places=2)
    currency = models.CharField(default='dollar', null=True, max_length=3)

    def __str__(self):
        return "%s: $%s/%s, Available: %s" %(self.description,
                                             self.unit_price,
                                             self.unit,
                                             self.quantity_in_stock)

class Invoice(models.Model):
    date_sent = models.DateField(null=True)
    date_due = models.DateField(null=True)
    bill_from = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='bill_from')
    bill_to = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='bill_to')
    terms = models.CharField(default='NET30', null=True, max_length=24, choices=TERM_CHOICES)
    total_price = models.DecimalField(default=None, null=True, max_digits=10, decimal_places=2)
    currency = models.CharField(default='dollar', null=True, max_length=3)
    is_flagged = models.BooleanField(default=False)
    is_scheduled = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.pk is None:
            super().save(*args, **kwargs)
        else:
            prices = Order.objects.filter(invoice=self.pk).values_list('item_total_price', flat=True)
            self.total_price = sum(prices)
            super().save(*args, **kwargs)

class Order(models.Model):
    invoice = models.ForeignKey(Invoice, null=True, on_delete=models.CASCADE, related_name='items')
    discount_code = models.ForeignKey(Discount, default=1, on_delete=models.CASCADE)
    item = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    quantity_purchased = models.DecimalField(max_digits=10, decimal_places=6)
    item_total_price = models.DecimalField(max_digits=10, decimal_places=6)

    def save(self, *args, **kwargs):
        unit_price = getattr(Inventory.objects.get(pk=self.item.pk), 'unit_price')
        self.item_total_price = self.quantity_purchased * unit_price
        super().save(*args, **kwargs)
