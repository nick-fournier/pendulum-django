from rest_framework import serializers
from .mail import *

class PlaidLinkTokenSerializer(serializers.ModelSerializer):
    public_token = serializers.CharField(required=True)
    plaid_id = serializers.CharField(required=True)

    class Meta:
        model = Business
        fields = ['public_token', 'plaid_id']
