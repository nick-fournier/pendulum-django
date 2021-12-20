from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from rest_framework.response import Response
from rest_framework import status
from .models import *
import datetime
import re
import sib_api_v3_sdk


#def send_notification(invoice_id, notif_type, to_email=None, cc=None, custom_text=None):
def send_notification(**args):

    # If any single item lists, unlist
    for key, value in args.items():
        if isinstance(value, list) and len(value) > 1:
            return Response({key, 'Received list instead of expected string type.'}, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(value, list) and len(value) <= 1:
            args[key] = value[0]
        else:
            args[key] = value


    # Check for optional items
    notif_type = args['notif_type'] if 'notif_type' in args else None
    cc = args['cc'] if 'cc' in args else None
    custom_text = args['custom_text'] if 'custom_text' in args else None

    # Pull items from invoice
    invoice = Invoice.objects.get(pk=args['invoice_id'])
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

        context = {'invoice': invoice,
                   'items': items,
                   'payment_url': payment_url}
        if CustomUser.objects.filter(business=invoice.bill_to).exists():
            context['user_name'] = CustomUser.objects.get(business=invoice.bill_to).first_name
        else:
            context['user_name'] = None

        # Getting email html context
        if invoice.terms not in ['COD', 'CIA', 'Custom'] and invoice.date_due is not None:
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

        # New/reminders go to bill_to, confirms also CC's bill_from
        subject = subjects[notif_type]
        from_email = 'notification@pendulumapp.com'  # settings.EMAIL_HOST_USER

        # Checking if CC emails are valid
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        invalid = []
        valid = []

        if cc:
            cc_list = [x.strip() for x in cc.split(",")]
            for email in cc_list:
                if (re.fullmatch(regex, email)):
                    valid.append(email)
                else:
                    invalid.append(email)

        if 'to_email' in args and (re.fullmatch(regex, args['to_email'])):
            to_email = args['to_email'] + valid
        else:
            to_email = [invoice.bill_to.business_email] + valid

        # if notif_type == 'confirm':
        #     to_email += [invoice.bill_from.business_email]

        text_content = text.render(context)
        html_content = html.render(context)

        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        msg.send()