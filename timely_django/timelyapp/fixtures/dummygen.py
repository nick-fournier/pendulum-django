import json
import random
import datetime
import copy
import os

class GenerateData:
    """
    1) Read base data:
    Read in the base dummy data containing templates for invoices and orders,
    also contains businesses, inventory items, and discount tables

    2) Generate invoice:
    Random events:
      - Pick to/from business
      - Pick terms  an assign dates
      - Pick flags (is flagged, paid, scheduled)

    2) Generate orders:
    Random events:
      - Pick item
      - Pick quantity
      - Calculate item total
      - Update invoice with total invoice price

    :param N_invoices: number of invoices to generate
    :param max_orders: maximum orders per invoice
    :return: returns a json database
    """

    def __init__(self, N_invoices, max_orders, fname):
        self.businesses = []
        self.inventory = []
        self.base_data = self.get_base_data()
        self.dummydata = self.gen_data(n=N_invoices, ordermax=max_orders)
        self.save(fname)

    def get_base_data(self):
        if 'dummy_base.json' in os.listdir():
            self.base_path = './'
        else:
            self.base_path = './timely_django/timelyapp/fixtures/'

        with open(self.base_path + 'dummy_base.json') as f:
            data = json.load(f)

        with open(self.base_path + 'users.json') as f:
            users = json.load(f)

        # Add user data
        data = data + users

        for i in range(len(data)):
            if data[i]['model'] == 'timelyapp.order':
                self.base_order = data[i]
            if data[i]['model'] == 'timelyapp.invoice':
                self.base_invoice = data[i]
            if data[i]['model'] == 'timelyapp.business':
                self.businesses.append(data[i])
            if data[i]['model'] == 'timelyapp.inventory':
                self.inventory.append(data[i])
            if data[i]['model'] == 'timelyapp.discount':
                self.discount = data[i]

        return data

    def get_invoice_name(self, bill_from, pk):
        words = bill_from['fields']['business_name'].split(" ")
        if len(words) > 1:
            name = ''.join([x[0] for x in words[:2]]).upper()
        else:
            name = bill_from['fields']['business_name'][:2].upper()
        name += str(datetime.date.today().year)[-2:]
        name += str(pk).zfill(6)
        return name

    def get_duedate(self, sent_date, terms):
        ndays = {'NET7': 7, 'NET10': 10, 'NET30': 30, 'NET60': 60, 'NET90': 90, 'NET120': 120}

        if terms in ndays:
            return (sent_date + datetime.timedelta(ndays[terms])).strftime("%Y-%m-%d")
        # elif terms in ['COD', 'CIA']:
        #     return {'COD': 'On delivery', 'CIA': 'Cash in advance'}[terms]
        else:
            return None

    def gen_data(self, n, ordermax):
        output_data = copy.deepcopy(self.base_data)
        TERM_CHOICES = ['COD', 'CIA', 'NET7', 'NET10', 'NET30', 'NET60', 'NET90', 'NET120']
        orderpk = 1

        for i in range(n):
            # Generate new invoice, need to add total price later
            new_invoice = copy.deepcopy(self.base_invoice)
            today = datetime.date.today()
            bill_to, bill_from = random.choices(self.businesses, k=2)
            date_sent = today + datetime.timedelta(random.randint(0, 180))

            new_invoice['pk'] = i+1
            new_invoice['fields']['invoice_name'] = self.get_invoice_name(bill_from, pk=i+1)
            new_invoice['fields']['terms'] = random.choice(TERM_CHOICES)
            new_invoice['fields']['date_sent'] = date_sent.strftime("%Y-%m-%d")
            new_invoice['fields']['bill_to'] = bill_to['pk']
            new_invoice['fields']['bill_from'] = bill_from['pk']
            new_invoice['fields']['date_due'] = self.get_duedate(date_sent, new_invoice['fields']['terms'])
            new_invoice['fields']['is_flagged'] = random.choice([True, False])
            new_invoice['fields']['is_scheduled'] = random.choice([True, False])
            new_invoice['fields']['is_paid'] = False if date_sent > today else random.choice([True, False])

            # Generate new order
            n_orders = random.randint(1, ordermax)
            items = random.choices(self.inventory, k=n_orders)
            subtotal = 0

            for j in range(len(items)):
                quantity = random.randint(1, ordermax)
                new_order = copy.deepcopy(self.base_order)

                new_order['pk'] = orderpk
                new_order['fields']['invoice'] = i+1
                new_order['fields']['discount_code'] = 1
                new_order['fields']['item'] = items[j]['pk']
                new_order['fields']['quantity_purchased'] = quantity
                new_order['fields']['item_total_price'] = items[j]['fields']['unit_price'] * quantity

                output_data.append(new_order)
                subtotal += new_order['fields']['item_total_price']
                orderpk += 1

            # Update total price
            new_invoice['fields']['total_price'] = subtotal
            output_data.append(new_invoice)

        return output_data

    def save(self, fname):
        if not '.json' in fname:
            fname += '.json'

        # Serializing to json string
        json_object = json.dumps(self.dummydata, indent=4)

        # Writing to .json
        with open(self.base_path + fname, 'w') as f:
            f.write(json_object)

if __name__ == "__main__":
   GenerateData(N_invoices=20, max_orders=10, fname='dummy.json')


