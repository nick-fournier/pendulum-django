from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context
from .models import *
import datetime

def send_new_invoice_email(invoice, items):
    if not invoice.terms == 'CIA':
        text = get_template('notifications/new_invoice_message.txt')
        html = get_template('notifications/new_invoice_message.html')

        url_dict = {'subdomain': 'dash.',
                    'domain': Site.objects.get_current().domain,
                    'path': '/invoice-payment',
                    'name': '/name=' + invoice.invoice_name,
                    'pk': '/id=' + str(invoice.pk)}
        payment_url = 'https://{subdomain}{domain}{path}{name}{pk}'.format(**url_dict)

        #context = {'user_name': invoice.bill_to.owner.first_name,
        context = {'user_name': CustomUser.objects.get(business=invoice.bill_to).first_name,
                   'invoice': invoice,
                   'items': items,
                   'payment_url': payment_url}

        if not invoice.terms in ['COD', 'CIA']:
            due_string = datetime.datetime.strptime(invoice.date_due, "%Y-%m-%d").date().strftime("%B %d, %Y")
            context['due_string'] = due_string
            context['due_statement'] = 'Please pay by ' + due_string + '.'

        subject = ' '.join(['New invoice from', invoice.bill_from.business_name, '[#' + invoice.invoice_name + ']'])
        from_email = settings.EMAIL_HOST_USER
        to_email = invoice.bill_to.business_email

        text_content = text.render(context)
        html_content = html.render(context)

        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
