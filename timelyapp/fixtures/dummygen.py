import json
import random
import datetime
import copy
import os
import shortuuid

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
        self.base_data = self.get_base_data()
        self.dummydata = self.gen_data(n=N_invoices, ordermax=max_orders)
        self.save(fname)

    def get_base_data(self):
        if 'dummy_base.json' in os.listdir():
            self.base_path = './'
        else:
            self.base_path = './timelyapp/fixtures/'

        with open(self.base_path + 'dummy_base.json') as f:
            data = json.load(f)

        with open(self.base_path + 'users.json') as f:
            users = json.load(f)

        # Add user data
        data = data + users

        self.businesses = []
        self.inventory = []
        self.base_invoice = []
        self.base_order = []
        self.discount = []
        self.taxes = []

        for i in range(len(data)):
            if data[i]['model'] == 'timelyapp.order':
                self.base_order.append(data[i])
            if data[i]['model'] == 'timelyapp.invoice':
                self.base_invoice.append(data[i])
            if data[i]['model'] == 'timelyapp.business':
                self.businesses.append(data[i])
            if data[i]['model'] == 'timelyapp.inventory':
                self.inventory.append(data[i])
            if data[i]['model'] == 'timelyapp.discount':
                self.discount.append(data[i])
            if data[i]['model'] == 'timelyapp.taxes':
                self.taxes.append(data[i])

        return data

    def get_invoice_name(self, bill_from, num):
        words = bill_from['fields']['business_name'].split(" ")
        if len(words) > 1:
            name = ''.join([x[0] for x in words[:2]]).upper()
        else:
            name = bill_from['fields']['business_name'][:2].upper()
        name += str(datetime.date.today().year)[-2:]
        name += str(num).zfill(6)
        return name

    def get_duedate(self, sent_date, terms):
        ndays = {'NET7': 7, 'NET10': 10, 'NET30': 30, 'NET60': 60, 'NET90': 90, 'NET120': 120}

        if terms in ndays:
            return (sent_date + datetime.timedelta(ndays[terms])).strftime("%Y-%m-%d")
        elif terms in ['CIA']:
            return sent_date.strftime("%Y-%m-%d")
        #     return {'COD': 'On delivery', 'CIA': 'Cash in advance'}[terms]
        else:
            return None

    def gen_data(self, n, ordermax):
        output_data = copy.deepcopy(self.base_data)
        TERM_CHOICES = ['COD', 'CIA', 'NET7', 'NET10', 'NET30', 'NET60', 'NET90', 'NET120']

        #Delete base invoice and order
        output_data = [x for x in output_data if not x.get('model') in ['timelyapp.invoice', 'timelyapp.order']]

        # Loop through n invoices
        for i in range(n):
            # Generate new invoice, need to add total price later
            # pick's invoice at random if multiple exist in data
            #new_invoice = copy.deepcopy(self.base_invoice)
            new_invoice = copy.deepcopy(self.base_invoice[random.randint(0, len(self.base_invoice)) - 1])
            today = datetime.date.today()
            bill_to, bill_from = random.sample(self.businesses, k=2) #without replacement so it cant be same business
            date_sent = today + datetime.timedelta(random.randint(0, 180))
            inv_id = "inv_" + shortuuid.uuid()

            new_invoice['pk'] = inv_id
            new_invoice['fields']['invoice_name'] = self.get_invoice_name(bill_from, num=i+1)
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
            subtotal, taxtotal = 0, 0

            # Loop through each item order nested in each invoice
            for j in range(len(items)):
                quantity = random.randint(1, ordermax)
                #new_order = copy.deepcopy(self.base_order)
                new_order = copy.deepcopy(self.base_order[random.randint(0, len(self.base_order)) - 1])
                new_order['pk'] = "ord_" + shortuuid.uuid()
                new_order['fields']['invoice'] = inv_id
                new_order['fields']['discount_code'] = 1
                new_order['fields']['item_name'] = items[j]['fields']['item_name']
                new_order['fields']['item_description'] = items[j]['fields']['description']
                new_order['fields']['quantity_purchased'] = quantity
                new_order['fields']['unit_price'] = items[j]['fields']['unit_price']
                new_order['fields']['item_price'] = new_order['fields']['unit_price'] * quantity

                # Loop through each tax rate associated with the invoice order
                itemtaxtot = 0
                if new_order['fields']['item_tax_rates']:
                    for tax in self.taxes:
                        if tax['pk'] in new_order['fields']['item_tax_rates']:
                            itemtaxtot += new_order['fields']['item_price'] * tax['fields']['percentage'] / 100
                new_order['fields']['item_tax_amt'] = itemtaxtot
                new_order['fields']['item_total_price'] = new_order['fields']['item_price'] + \
                                                          new_order['fields']['item_tax_amt']
                output_data.append(new_order)
                subtotal += new_order['fields']['item_total_price']
                taxtotal += new_order['fields']['item_tax_amt']


            # Update total price
            new_invoice['fields']['invoice_price'] = subtotal
            new_invoice['fields']['invoice_tax_amt'] = taxtotal
            new_invoice['fields']['invoice_total_price'] = subtotal + taxtotal
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
    # ordermax = 10
    # n = 20
    # i, j, k = 0, 0, 0
    test = GenerateData(N_invoices=20, max_orders=10, fname='dummy.json')


