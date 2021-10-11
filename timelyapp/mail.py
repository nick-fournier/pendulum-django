from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from .models import *
import datetime
import sib_api_v3_sdk


def send_notification(invoice_id, type):

    # Pull items from invoice
    invoice = Invoice.objects.get(pk=invoice_id)
    items = Order.objects.filter(invoice=invoice)

    templates = {'new': 'new_invoice_message',
                 'remind': 'remind_invoice_message',
                 'confirm': 'confirm_payment_message'}

    subjects = {
        'New invoice from {biz} [# {id}]'.format(biz=invoice.bill_from.business_name, id=invoice.invoice_name),
        'Invoice reminder [# {id}]'.format(biz=invoice.bill_from.business_name, id=invoice.invoice_name),
        'Payment confirmation [# {id}]'.format(biz=invoice.bill_from.business_name, id=invoice.invoice_name)
                }


    if not invoice.terms == 'CIA':
        text = get_template('notifications/{type}.txt'.format(type=templates[type]))
        html = get_template('notifications/{type}.html'.format(type=templates[type]))

        url_dict = {'subdomain': 'dash.',
                    'domain': Site.objects.get_current().domain,
                    'path': '/pay/',
                    'pk': str(invoice.pk)}
        payment_url = 'https://{subdomain}{domain}{path}{pk}'.format(**url_dict)

        context = {'user_name': CustomUser.objects.get(business=invoice.bill_to).first_name,
                   'invoice': invoice,
                   'items': items,
                   'payment_url': payment_url}

        if not invoice.terms in ['COD', 'CIA']:
            due_string = datetime.datetime.strptime(invoice.date_due, "%Y-%m-%d").date().strftime("%B %d, %Y")
            context['due_string'] = due_string
            context['due_statement'] = 'Please pay by ' + due_string + '.'


        subject = subjects[type]
        from_email = 'notification@pendulumapp.com' #settings.EMAIL_HOST_USER
        to_email = invoice.bill_to.business_email

        text_content = text.render(context)
        html_content = html.render(context)

        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()


def send_new_invoice_email(invoice_id):

    # Pull items from invoice
    invoice = Invoice.objects.get(pk=invoice_id)
    items = Order.objects.filter(invoice=invoice)

    if not invoice.terms == 'CIA':
        text = get_template('notifications/new_invoice_message.txt')
        html = get_template('notifications/new_invoice_message.html')

        url_dict = {'subdomain': 'dash.',
                    'domain': Site.objects.get_current().domain,
                    'path': '/pay/',
                    #'name': invoice.invoice_name,
                    'pk': str(invoice.pk)}
        payment_url = 'https://{subdomain}{domain}{path}{pk}'.format(**url_dict)

        context = {'user_name': CustomUser.objects.get(business=invoice.bill_to).first_name,
                   'invoice': invoice,
                   'items': items,
                   'payment_url': payment_url}

        if not invoice.terms in ['COD', 'CIA']:
            due_string = datetime.datetime.strptime(invoice.date_due, "%Y-%m-%d").date().strftime("%B %d, %Y")
            context['due_string'] = due_string
            context['due_statement'] = 'Please pay by ' + due_string + '.'

        subject = ' '.join(['New invoice from', invoice.bill_from.business_name, '[#' + invoice.invoice_name + ']'])
        from_email = 'notification@pendulumapp.com' #settings.EMAIL_HOST_USER
        to_email = invoice.bill_to.business_email

        text_content = text.render(context)
        html_content = html.render(context)

        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

def send_remind_invoice_email(invoice_id):

    # Pull items from invoice
    invoice = Invoice.objects.get(pk=invoice_id)
    items = Order.objects.filter(invoice=invoice)

    if not invoice.terms == 'CIA':
        text = get_template('notifications/remind_invoice_message.txt')
        html = get_template('notifications/remind_invoice_message.html')

        url_dict = {'subdomain': 'dash.',
                    'domain': Site.objects.get_current().domain,
                    'path': '/pay/',
                    #'name': invoice.invoice_name,
                    'pk': str(invoice.pk)}
        payment_url = 'https://{subdomain}{domain}{path}{pk}'.format(**url_dict)

        context = {'user_name': CustomUser.objects.get(business=invoice.bill_to).first_name,
                   'invoice': invoice,
                   'items': items,
                   'payment_url': payment_url}

        if not invoice.terms in ['COD', 'CIA']:
            due_string = invoice.date_due.strftime("%B %d, %Y")
            context['due_string'] = due_string
            context['due_statement'] = 'Please pay by ' + due_string + '.'

        subject = ' '.join(['New invoice from', invoice.bill_from.business_name, '[#' + invoice.invoice_name + ']'])
        from_email = 'notification@pendulumapp.com' #settings.EMAIL_HOST_USER
        to_email = invoice.bill_to.business_email

        text_content = text.render(context)
        html_content = html.render(context)

        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

def send_payment_confirmation(invoice_id):

    # Pull items from invoice
    invoice = Invoice.objects.get(pk=invoice_id)
    items = Order.objects.filter(invoice=invoice)

    if not invoice.terms == 'CIA':
        text = get_template('notifications/confirmation_payment_message.txt')
        html = get_template('notifications/confirmation_payment_message.html')

        url_dict = {'subdomain': 'dash.',
                    'domain': Site.objects.get_current().domain,
                    'path': '/pay/',
                    #'name': invoice.invoice_name,
                    'pk': str(invoice.pk)}
        payment_url = 'https://{subdomain}{domain}{path}{pk}'.format(**url_dict)

        context = {'user_name': CustomUser.objects.get(business=invoice.bill_to).first_name,
                   'invoice': invoice,
                   'items': items,
                   'payment_url': payment_url}

        if not invoice.terms in ['COD', 'CIA']:
            due_string = invoice.date_due.strftime("%B %d, %Y")
            context['due_string'] = due_string
            context['due_statement'] = 'Please pay by ' + due_string + '.'

        subject = ' '.join(['New invoice from', invoice.bill_from.business_name, '[#' + invoice.invoice_name + ']'])
        from_email = 'notification@pendulumapp.com' #settings.EMAIL_HOST_USER
        to_email = invoice.bill_to.business_email

        text_content = text.render(context)
        html_content = html.render(context)

        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()