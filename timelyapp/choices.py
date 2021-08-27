from django.utils.translation import ugettext as _

EMPLOYEES_CHOICES = [
    ('1-10', '1-10'),
    ('11-30', '11-30'),
    ('31-50', '31-50'),
    ('51-100', '51-100'),
    ('100+', '100+'),
]

QROLE_CHOICES = [
    ('Employee', 'Employee'),
    ('MANAGER', 'Management'),
    ('OWNER', 'Business owner'),
]

TERM_CHOICES = [
    ('Custom', 'Custom due date'),
    ('COD', 'Cash on delivery'),
    ('CIA', 'Cash in advance'),
    ('NET7', 'Net 7 days'),
    ('NET10', 'Net 10 days'),
    ('NET30', 'Net 30 days'),
    ('NET60', 'Net 60 days'),
    ('NET90', 'Net 90 days'),
    ('NET120', 'Net 120 days'),
]

PAYMENT_CHOICES = [
    ('ACH', 'Bank transfer'),
    ('CHECK', 'Check'),
    ('CREDIT', 'Credit card'),
    ('LATER', 'Pay later with Timely'),
    ('FINANCE', 'Invoice financing with Timely'),
]

ROLE_CHOICES = [
    ('SALES STAFF', 'Sales Staff can view receivables only'),
    ('PURCHASING STAFF', 'Purchasing Staff can view payables only'),
    ('STAFF', 'Staff can view all invoices, but only view'),
    ('SALES MANAGER', 'Sales Manager can generate invoices / approve purchase orders'),
    ('PURCHASING MANAGER', 'Purchasing Manager can approve invoices / generate purchase order'),
    ('MANAGER', 'Manager has full access to payables and receivables'),
    ('CONTROLLER', 'Controller has full access to payables/receivables and can change user permissions'),
    ('OWNER', 'Owner has full access and is irrevocable'),
]

STATES_CHOICES = (
    ('AL', _('Alabama')),
    ('AZ', _('Arizona')),
    ('AR', _('Arkansas')),
    ('CA', _('California')),
    ('CO', _('Colorado')),
    ('CT', _('Connecticut')),
    ('DE', _('Delaware')),
    ('DC', _('District of Columbia')),
    ('FL', _('Florida')),
    ('GA', _('Georgia')),
    ('ID', _('Idaho')),
    ('IL', _('Illinois')),
    ('IN', _('Indiana')),
    ('IA', _('Iowa')),
    ('KS', _('Kansas')),
    ('KY', _('Kentucky')),
    ('LA', _('Louisiana')),
    ('ME', _('Maine')),
    ('MD', _('Maryland')),
    ('MA', _('Massachusetts')),
    ('MI', _('Michigan')),
    ('MN', _('Minnesota')),
    ('MS', _('Mississippi')),
    ('MO', _('Missouri')),
    ('MT', _('Montana')),
    ('NE', _('Nebraska')),
    ('NV', _('Nevada')),
    ('NH', _('New Hampshire')),
    ('NJ', _('New Jersey')),
    ('NM', _('New Mexico')),
    ('NY', _('New York')),
    ('NC', _('North Carolina')),
    ('ND', _('North Dakota')),
    ('OH', _('Ohio')),
    ('OK', _('Oklahoma')),
    ('OR', _('Oregon')),
    ('PA', _('Pennsylvania')),
    ('RI', _('Rhode Island')),
    ('SC', _('South Carolina')),
    ('SD', _('South Dakota')),
    ('TN', _('Tennessee')),
    ('TX', _('Texas')),
    ('UT', _('Utah')),
    ('VT', _('Vermont')),
    ('VA', _('Virginia')),
    ('WA', _('Washington')),
    ('WV', _('West Virginia')),
    ('WI', _('Wisconsin')),
    ('WY', _('Wyoming')),
    ('AK', _('Alaska')),
    ('HI', _('Hawaii')),
    ('AS', _('American Samoa')),
    ('GU', _('Guam')),
    ('MP', _('Northern Mariana Islands')),
    ('PR', _('Puerto Rico')),
    ('VI', _('Virgin Islands')),
    ('AA', _('Armed Forces Americas')),
    ('AE', _('Armed Forces Europe')),
    ('AP', _('Armed Forces Pacific')),
    ('FM', _('Federated States of Micronesia')),
    ('MH', _('Marshall Islands')),
    ('PW', _('Palau')),
)
