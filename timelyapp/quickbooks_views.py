from django.conf import settings
from intuitlib.client import AuthClient
from quickbooks.objects.customer import Customer
from quickbooks import QuickBooks

QB_CLIENT_ID = 'AB5v4IRFN0J5CFgirIIi6iUJI0FKjBuVgvOZc7OiPsm1hncZax'
QB_CLIENT_SECRET = 'CwezjGPgzupc3XBW83EHFVAnd0d1utkY5Y5JZztN'

auth_client = AuthClient(
        client_id=QB_CLIENT_ID,
        client_secret=QB_CLIENT_SECRET,
        #access_token='ACCESS_TOKEN',  # If you do not pass this in, the Quickbooks client will call refresh and get a new access token.
        environment='sandbox',
        redirect_uri='http://localhost:8000/callback',
    )

client = QuickBooks(
        auth_client=auth_client,
        refresh_token='REFRESH_TOKEN',
        company_id='COMPANY_ID',
    )

customers = Customer.all(qb=client)