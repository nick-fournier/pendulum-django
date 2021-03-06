import datetime
import json
import numpy as np
import pandas as pd
from .mail import *


def calculate_duedate(data):
    terms = data['terms']
    today = datetime.date.today()
    ndays = {'NET7': 7, 'NET10': 10, 'NET30': 30, 'NET60': 60, 'NET90': 90, 'NET120': 120}

    if terms in ndays:
        return (today + datetime.timedelta(ndays[terms])).strftime("%Y-%m-%d")
    if terms == 'Custom':
        return data['date_due'] #.strftime("%Y-%m-%d")
    if terms == 'CIA':
        return today
    if terms == 'COD':
        return None
    else:
        return None


def generate_invoice_name(bill_from_id):
    name = Business.objects.get(pk=bill_from_id).business_name
    n = Invoice.objects.filter(bill_from__id=bill_from_id).count()

    words = name.split(" ")
    if len(words) > 1:
        name = ''.join([x[0] for x in words[:2]]).upper()
    else:
        name = name[:2].upper()
    name += str(datetime.date.today().year)[-2:]
    name += str(n).zfill(6)
    return name


def calculate_prices(items):
    total_price = 0
    for i in range(len(items)):
        unit_price = getattr(Inventory.objects.get(pk=items[i]['item'].pk), 'unit_price')
        items[i] = {**items[i], **{'item_total_price': unit_price * items[i]['quantity_purchased']}}
        total_price += items[i]['item_total_price']
    return items, total_price


def type_converter(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, datetime.datetime):
        return obj.__str__()


def get_business_id(user_id):
    try:
        return Business.objects.get(owner__id=user_id).id
    except Business.DoesNotExist:
        return None


def get_invoices(biz_id, invoice_type):
    if invoice_type == "receivables":
        invoices = Invoice.objects.filter(bill_from__id=biz_id).values()
        opposite = "bill_to_id"

    elif invoice_type == "payables":
        invoices = Invoice.objects.filter(bill_to__id=biz_id).values()
        opposite = "bill_from_id"
    else:
        return None

    if invoices.exists():
        # Gets the other business's data
        other_business = Business.objects.filter(pk=invoices[0][opposite]).values()
        order = Order.objects.filter(invoice__in=invoices.values_list('id', flat=True)).values()

        # Convert to data frame to merge
        invoices = pd.DataFrame(invoices).rename(columns={'id': 'invoice_id'})
        other_business = pd.DataFrame(other_business).rename(columns={'id': 'business_id'})
        order = pd.DataFrame(order)

        invoices_merged = invoices.merge(other_business,
                                         left_on=opposite,
                                         right_on='business_id')

        # Some formatting fixes
        invoices_merged.total_price.fillna(0, inplace=True)
        invoices_merged.total_price = '$' + invoices_merged.total_price.astype('float').round(2).astype(str)
        invoices_merged.date_sent = [x.strftime("%B %d, %Y").lstrip("0") for x in invoices_merged.date_sent]
        invoices_merged.date_due = ['COD' if x is None else x.strftime("%B %d, %Y").lstrip("0") for x in
                                    invoices_merged.date_due]

        invoices_merged = invoices_merged.sort_values('date_due', ascending=False).reset_index(drop=True)
        # invoices_merged.set_index('invoice_id', inplace=True)

        # Convert to JSON
        data_dict_list = []
        for i in range(len(invoices_merged)):
            invoice_id = invoices_merged.iloc[i].invoice_id
            invoice_dict = invoices_merged.iloc[i]
            order_dict = order[order.invoice_id == invoice_id].to_dict(orient='records')
            data_dict_list.append({**invoice_dict, **{"order_list": order_dict}})

        # This parses it to make sure any weird data types are smoothed out
        data_json = json.dumps(data_dict_list, indent=4, default=type_converter)
        data = list(json.loads(data_json))

        return data


# Create invoice function
def create_invoice(validated_data, business, bill_to_from):
    validated_data[bill_to_from] = business
    validated_data['date_sent'] = datetime.date.today()
    validated_data['date_due'] = calculate_duedate(validated_data)

    if 'invoice_name' not in validated_data or validated_data['invoice_name'] == "":
        validated_data['invoice_name'] = generate_invoice_name(business.pk)

    # Pop out many-to-many payment field. Need to create invoice before assigning
    if 'accepted_payments' in validated_data:
        accepted_payments = validated_data.pop('accepted_payments')
    else:
        accepted_payments = []

    # If itemized, pop out. Need to create invoice before linking
    if 'items' in validated_data:
        items_list = validated_data.pop('items')
        items_data = []
        validated_data['invoice_only'] = False
        validated_data['invoice_tax_amt'] = 0
        validated_data['invoice_price'] = 0

        for item in items_list:
            # Remove empty description field if blank ""
            if item['item_description'] == "":
                item['item_description'] = None

            # Calculate item sub-total price | Should I check if not empty?
            item['item_price'] = item['quantity_purchased'] * item['unit_price']

            # Calculate tax
            item['item_tax_amt'] = 0
            for tax in item['item_tax_rates']:
                item['item_tax_amt'] += item['item_price'] * tax.percentage / 100

            # Calculate price + tax
            item['item_total_price'] = item['item_price'] + item['item_tax_amt']

            # if 'item_tax_amt' in validated_data:
            validated_data['invoice_tax_amt'] += item['item_tax_amt']
            # if 'invoice_price' not in validated_data:
            validated_data['invoice_price'] += item['item_price']
            # if 'invoice_total_price' not in validated_data:
            validated_data['invoice_total_price'] = validated_data['invoice_tax_amt'] + validated_data['invoice_price']
            items_data.append(item)


        # Now create invoice and assign linked orders
        invoice = Invoice.objects.create(**validated_data)

        for item in items_data:
            # If new item, add to inventory
            if item['is_new']:
                new_item = {'item_name': item['item_name'],
                            'unit_price': item['unit_price'],
                            'description': item['item_description']}
                Inventory.objects.create(business=business, **new_item)
            item.pop('is_new')

            # Pop out many-to-many payment field. Need to create item order before assigning
            if 'item_tax_rates' in item:
                tax_rates = item.pop('item_tax_rates')
            else:
                tax_rates = []
            # Create the order
            order = Order.objects.create(invoice=invoice, **item)

            # Once order is created, assign payment M2M field
            for tax in tax_rates:
                order.item_tax_rates.add(tax)
    else:
        validated_data['invoice_only'] = True
        invoice = Invoice.objects.create(**validated_data)

    # Once invoice is created, assign payment M2M field
    for payment in accepted_payments:
        invoice.accepted_payments.add(payment)

    # Send email
    if bill_to_from == 'bill_from':
        send_notification(invoice_id=invoice.id, notif_type='new')

    return invoice
