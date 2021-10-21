from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from .models import *
import datetime
import re
import sib_api_v3_sdk


def send_notification(invoice_id, notif_type, cc=None, custom_text=None):

    # Pull items from invoice
    invoice = Invoice.objects.get(pk=invoice_id)
    items = Order.objects.filter(invoice=invoice)

    # Select template type
    templates = {
        'new': 'new_invoice_message',
        'remind': 'remind_invoice_message',
        'confirm': 'confirm_payment_message'
    }

    # Select subject type
    subjects = {
        'new': 'New invoice from {biz} [# {id}]'.format(biz=invoice.bill_from.business_name, id=invoice.invoice_name),
        'remind': 'Invoice reminder [# {id}]'.format(biz=invoice.bill_from.business_name, id=invoice.invoice_name),
        'confirm': 'Payment confirmation [# {id}]'.format(biz=invoice.bill_from.business_name, id=invoice.invoice_name)
    }

    default_text = {'new': 'Thanks for using {biz}',
                    'remind': 'This is just a friendly reminder that you have an invoice of ${amt} due. \nThank you for using {biz}',
                    'confirm': 'This is a confirmation email for your payment of ${amt} to {biz} for Invoice #{id}.'
                    }

    if not invoice.terms == 'CIA':
        text = get_template('notifications/{type}.txt'.format(type=templates[notif_type]))
        html = get_template('notifications/{type}.html'.format(type=templates[notif_type]))

        url_dict = {'subdomain': 'dash.',
                    'domain': Site.objects.get_current().domain,
                    'path': '/pay/',
                    'pk': str(invoice.pk)}
        payment_url = 'https://{subdomain}{domain}{path}{pk}'.format(**url_dict)

        context = {'user_name': CustomUser.objects.get(business=invoice.bill_to).first_name,
                   'invoice': invoice,
                   'items': items,
                   'payment_url': payment_url}

        # Getting email html context
        if not invoice.terms in ['COD', 'CIA']:
            due_string = invoice.date_due.strftime("%B %d, %Y")
            context['due_string'] = due_string
            context['due_statement'] = 'Please pay by ' + due_string + '.'
        else:
            context['due_statement'] = None

        if custom_text:
            context['custom_text'] = custom_text
        else:
            context['custom_text'] = default_text[notif_type].format(amt=str(round(invoice.invoice_total_price, 2)),
                                                                     biz=invoice.bill_from.business_name,
                                                                     id=invoice.invoice_name)

        # Checking if CC emails are valid
        invalid = []
        valid = []
        if cc:
            cc_list = [x.strip() for x in cc.split(",")]
            regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            for email in cc_list:
                if (re.fullmatch(regex, email)):
                    valid.append(email)
                else:
                    invalid.append(email)

        # New/reminders go to bill_to, confirms also CC's bill_from
        subject = subjects[notif_type]
        from_email = 'notification@pendulumapp.com'  # settings.EMAIL_HOST_USER
        to_email = [invoice.bill_to.business_email] + valid
        if notif_type == 'confirm':
            to_email += [invoice.bill_from.business_email]

        text_content = text.render(context)
        html_content = html.render(context)

        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        msg.send()


# def send_new_invoice_email(invoice_id):
#
#     # Pull items from invoice
#     invoice = Invoice.objects.get(pk=invoice_id)
#     items = Order.objects.filter(invoice=invoice)
#
#     if not invoice.terms == 'CIA':
#         text = get_template('notifications/new_invoice_message.txt')
#         html = get_template('notifications/new_invoice_message.html')
#
#         url_dict = {'subdomain': 'dash.',
#                     'domain': Site.objects.get_current().domain,
#                     'path': '/pay/',
#                     #'name': invoice.invoice_name,
#                     'pk': str(invoice.pk)}
#         payment_url = 'https://{subdomain}{domain}{path}{pk}'.format(**url_dict)
#
#         context = {'user_name': CustomUser.objects.get(business=invoice.bill_to).first_name,
#                    'invoice': invoice,
#                    'items': items,
#                    'payment_url': payment_url}
#
#         if not invoice.terms in ['COD', 'CIA']:
#             due_string = datetime.datetime.strptime(invoice.date_due, "%Y-%m-%d").date().strftime("%B %d, %Y")
#             context['due_string'] = due_string
#             context['due_statement'] = 'Please pay by ' + due_string + '.'
#
#         subject = ' '.join(['New invoice from', invoice.bill_from.business_name, '[#' + invoice.invoice_name + ']'])
#         from_email = 'notification@pendulumapp.com' #settings.EMAIL_HOST_USER
#         to_email = invoice.bill_to.business_email
#
#         text_content = text.render(context)
#         html_content = html.render(context)
#
#         msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
#         msg.attach_alternative(html_content, "text/html")
#         msg.send()

# def send_remind_invoice_email(invoice_id):
#
#     # Pull items from invoice
#     invoice = Invoice.objects.get(pk=invoice_id)
#     items = Order.objects.filter(invoice=invoice)
#
#     if not invoice.terms == 'CIA':
#         text = get_template('notifications/remind_invoice_message.txt')
#         html = get_template('notifications/remind_invoice_message.html')
#
#         url_dict = {'subdomain': 'dash.',
#                     'domain': Site.objects.get_current().domain,
#                     'path': '/pay/',
#                     #'name': invoice.invoice_name,
#                     'pk': str(invoice.pk)}
#         payment_url = 'https://{subdomain}{domain}{path}{pk}'.format(**url_dict)
#
#         context = {'user_name': CustomUser.objects.get(business=invoice.bill_to).first_name,
#                    'invoice': invoice,
#                    'items': items,
#                    'payment_url': payment_url}
#
#         if not invoice.terms in ['COD', 'CIA']:
#             due_string = invoice.date_due.strftime("%B %d, %Y")
#             context['due_string'] = due_string
#             context['due_statement'] = 'Please pay by ' + due_string + '.'
#
#         subject = ' '.join(['New invoice from', invoice.bill_from.business_name, '[#' + invoice.invoice_name + ']'])
#         from_email = 'notification@pendulumapp.com' #settings.EMAIL_HOST_USER
#         to_email = invoice.bill_to.business_email
#
#         text_content = text.render(context)
#         html_content = html.render(context)
#
#         msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
#         msg.attach_alternative(html_content, "text/html")
#         msg.send()

# def send_payment_confirmation(invoice_id):
#
#     # Pull items from invoice
#     invoice = Invoice.objects.get(pk=invoice_id)
#     items = Order.objects.filter(invoice=invoice)
#
#     if not invoice.terms == 'CIA':
#         text = get_template('notifications/confirmation_payment_message.txt')
#         html = get_template('notifications/confirmation_payment_message.html')
#
#         url_dict = {'subdomain': 'dash.',
#                     'domain': Site.objects.get_current().domain,
#                     'path': '/pay/',
#                     #'name': invoice.invoice_name,
#                     'pk': str(invoice.pk)}
#         payment_url = 'https://{subdomain}{domain}{path}{pk}'.format(**url_dict)
#
#         context = {'user_name': CustomUser.objects.get(business=invoice.bill_to).first_name,
#                    'invoice': invoice,
#                    'items': items,
#                    'payment_url': payment_url}
#
#         if not invoice.terms in ['COD', 'CIA']:
#             due_string = invoice.date_due.strftime("%B %d, %Y")
#             context['due_string'] = due_string
#             context['due_statement'] = 'Please pay by ' + due_string + '.'
#
#         subject = ' '.join(['New invoice from', invoice.bill_from.business_name, '[#' + invoice.invoice_name + ']'])
#         from_email = 'notification@pendulumapp.com' #settings.EMAIL_HOST_USER
#         to_email = invoice.bill_to.business_email
#
#         text_content = text.render(context)
#         html_content = html.render(context)
#
#         msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
#         msg.attach_alternative(html_content, "text/html")
#         msg.send()