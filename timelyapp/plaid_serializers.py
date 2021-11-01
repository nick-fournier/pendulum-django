from rest_framework import serializers
from .mail import *

class PlaidLinkTokenSerializer(serializers.ModelSerializer):
    public_token = serializers.CharField(required=True)

    class Meta:
        model = Business
        fields = ['public_token']
