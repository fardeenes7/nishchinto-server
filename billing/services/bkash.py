"""
billing/services/bkash.py

Service layer for bKash Tokenized Checkout API.
Supports Agreement creation, Payment execution, and Partial Refunds.
"""

import json
import logging
import requests
from django.conf import settings
from django.utils import timezone
from billing.models import PaymentGatewayConfig, BKashAgreement, PaymentTransaction, RefundRecord

logger = logging.getLogger(__name__)

class BKashService:
    """
    Handles tokenized bKash operations.
    """

    def __init__(self, shop):
        self.shop = shop
        self.config = PaymentGatewayConfig.objects.get(
            shop=shop, 
            gateway=PaymentGatewayConfig.GATEWAY_BKASH,
            is_active=True
        )
        self.creds = json.loads(self.config.credentials_encrypted)
        
        self.base_url = "https://tokenized.pay.bka.sh/v1.2.0-beta" if not self.config.is_test_mode else "https://tokenized.sandbox.bka.sh/v1.2.0-beta"
        self.app_key = self.creds.get('app_key')
        self.app_secret = self.creds.get('app_secret')
        self.username = self.creds.get('username')
        self.password = self.creds.get('password')

    def _get_headers(self, token=None):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "username": self.username,
            "password": self.password,
        }
        if token:
            headers["authorization"] = token
            headers["x-app-key"] = self.app_key
        return headers

    def grant_token(self):
        """
        Retrieves id_token from bKash.
        """
        url = f"{self.base_url}/tokenized/checkout/token/grant"
        payload = {
            "app_key": self.app_key,
            "app_secret": self.app_secret
        }
        response = requests.post(url, json=payload, headers=self._get_headers())
        data = response.json()
        if response.status_code == 200:
            return data.get('id_token')
        raise Exception(f"bKash Token Grant Failed: {data.get('statusMessage', 'Unknown Error')}")

    def create_agreement(self, payer_reference, callback_url):
        """
        Initiates bKash Agreement creation.
        Returns the bkashURL for the customer to redirect to.
        """
        token = self.grant_token()
        url = f"{self.base_url}/tokenized/checkout/agreement/create"
        payload = {
            "mode": "0000", # Agreement creation
            "payerReference": payer_reference,
            "callbackURL": callback_url
        }
        response = requests.post(url, json=payload, headers=self._get_headers(token))
        return response.json()

    def execute_agreement(self, payment_id):
        """
        Finalizes agreement after customer approval.
        """
        token = self.grant_token()
        url = f"{self.base_url}/tokenized/checkout/agreement/execute"
        payload = {"paymentID": payment_id}
        response = requests.post(url, json=payload, headers=self._get_headers(token))
        data = response.json()
        
        if data.get('statusCode') == '0000':
            # Save agreement
            BKashAgreement.objects.create(
                shop=self.shop,
                tenant_id=self.shop.id,
                agreement_id=data.get('agreementID'),
                payer_reference=data.get('payerReference'),
                customer_identifier=data.get('customerMsisdn'),
            )
        return data

    def create_payment(self, agreement_id, amount, merchant_invoice, callback_url):
        """
        Creates a payment using an existing agreement.
        """
        token = self.grant_token()
        url = f"{self.base_url}/tokenized/checkout/payment/create"
        payload = {
            "mode": "0001", # Agreement based payment
            "payerReference": merchant_invoice,
            "callbackURL": callback_url,
            "amount": str(amount),
            "currency": "BDT",
            "intent": "sale",
            "merchantInvoiceNumber": merchant_invoice,
            "agreementID": agreement_id
        }
        response = requests.post(url, json=payload, headers=self._get_headers(token))
        return response.json()

    def execute_payment(self, payment_id):
        """
        Executes and captures the payment.
        """
        token = self.grant_token()
        url = f"{self.base_url}/tokenized/checkout/payment/execute"
        payload = {"paymentID": payment_id}
        response = requests.post(url, json=payload, headers=self._get_headers(token))
        data = response.json()
        
        if data.get('statusCode') == '0000':
            # Record transaction
            PaymentTransaction.objects.create(
                shop=self.shop,
                tenant_id=self.shop.id,
                gateway=PaymentGatewayConfig.GATEWAY_BKASH,
                external_transaction_id=data.get('trxID'),
                amount=data.get('amount'),
                status=PaymentTransaction.STATUS_COMPLETED,
                gateway_response=data
            )
        return data

    def refund(self, trx_id, payment_id, amount, reason=""):
        """
        Partial or full refund. Supports up to 10 refunds per payment.
        """
        token = self.grant_token()
        url = f"{self.base_url}/tokenized/checkout/payment/refund"
        payload = {
            "paymentID": payment_id,
            "amount": str(amount),
            "trxID": trx_id,
            "reason": reason,
            "sku": "refund"
        }
        response = requests.post(url, json=payload, headers=self._get_headers(token))
        data = response.json()
        
        if data.get('statusCode') == '0000':
            # Record refund
            transaction = PaymentTransaction.objects.get(external_transaction_id=trx_id)
            RefundRecord.objects.create(
                shop=self.shop,
                tenant_id=self.shop.id,
                transaction=transaction,
                amount=amount,
                reason=reason,
                external_refund_id=data.get('refundTrxID'),
                gateway_response=data
            )
            # Update transaction status
            transaction.status = PaymentTransaction.STATUS_PARTIALLY_REFUNDED
            transaction.save()
            
        return data
