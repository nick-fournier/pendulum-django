import datetime
import json
import numpy as np

from .models import *

def calculate_duedate(terms):
    today = datetime.date.today()
    ndays = {'NET7': 7, 'NET10': 10, 'NET30': 30, 'NET60': 60, 'NET90': 90, 'NET120': 120}

    if terms in ndays:
        return (today + datetime.timedelta(ndays[terms])).strftime("%Y-%m-%d")
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


def get_invoices(biz_id, type):
    if type == "receivables":
        invoices = Invoice.objects.filter(bill_from__id=biz_id).values()
        opposite = "bill_to_id"

    elif type == "payables":
        invoices = Invoice.objects.filter(bill_to__id=biz_id).values()
        opposite = "bill_from_id"
    else:
        return None

    if invoices.exists():
        #Gets the other business's data
        other_business = Business.objects.filter(pk=invoices[0][opposite]).values()
        order = Order.objects.filter(invoice__in=invoices.values_list('id', flat=True)).values()

        #Convert to data frame to merge
        invoices = pd.DataFrame(invoices).rename(columns={'id': 'invoice_id'})
        other_business = pd.DataFrame(other_business).rename(columns={'id': 'business_id'})
        order = pd.DataFrame(order)

        invoices_merged = invoices.merge(other_business,
                            left_on=opposite,
                            right_on='business_id')

        #Some formatting fixes
        invoices_merged.total_price.fillna(0, inplace=True)
        invoices_merged.total_price = '$' + invoices_merged.total_price.astype('float').round(2).astype(str)
        invoices_merged.date_sent = [x.strftime("%B %d, %Y").lstrip("0") for x in invoices_merged.date_sent]
        invoices_merged.date_due = ['COD' if x is None else x.strftime("%B %d, %Y").lstrip("0") for x in invoices_merged.date_due]

        invoices_merged = invoices_merged.sort_values('date_due', ascending=False).reset_index(drop=True)
        # invoices_merged.set_index('invoice_id', inplace=True)

        #Convert to JSON
        data_dict_list = []
        for i in range(len(invoices_merged)):
            invoice_id = invoices_merged.iloc[i].invoice_id
            invoice_dict = invoices_merged.iloc[i]
            order_dict = order[order.invoice_id == invoice_id].to_dict(orient='records')
            data_dict_list.append({**invoice_dict, **{"order_list": order_dict}})

        #This parses it to make sure any weird data types are smoothed out
        data_json = json.dumps(data_dict_list, indent=4, default=type_converter)
        data = list(json.loads(data_json))

        return data

