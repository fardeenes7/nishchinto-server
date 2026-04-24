"""
billing/services/checkout.py

High-level service for handling checkout payment flows.
Coordinates between Order models and Payment Gateways.
"""

import logging
from django.utils import timezone
from django.db import transaction

from orders.models import Order, OrderStatus, PaymentInvoice
from billing.models import BKashAgreement, PaymentGatewayConfig, PaymentTransaction
from billing.services.bkash import BKashService

logger = logging.getLogger(__name__)

class CheckoutService:
    """
    Manages the lifecycle of a payment for a specific order.
    """

    def __init__(self, shop_id):
        from shops.models import Shop
        self.shop = Shop.objects.get(id=shop_id)

    def initiate_payment(self, invoice_token: str, gateway: str, callback_url: str):
        """
        Entry point for checkout.
        """
        try:
            invoice = PaymentInvoice.objects.select_related('order').get(
                token=invoice_token, 
                is_used=False,
                expires_at__gt=timezone.now()
            )
        except PaymentInvoice.DoesNotExist:
            raise ValueError("Invalid or expired payment invoice.")

        order = invoice.order
        
        if gateway == PaymentGatewayConfig.GATEWAY_BKASH:
            return self._initiate_bkash_flow(order, callback_url)
        else:
            raise ValueError(f"Gateway {gateway} not supported for online checkout yet.")

    def _initiate_bkash_flow(self, order: Order, callback_url: str):
        """
        Checks for existing agreement or creates a new one.
        """
        bkash = BKashService(self.shop)
        
        # Check for agreement by customer identifier (msisdn/phone)
        # In a real scenario, we might have the customer's phone in the order or profile
        customer_phone = order.customer_profile.phone if order.customer_profile else "GUEST"
        
        agreement = BKashAgreement.objects.filter(
            shop=self.shop,
            customer_identifier=customer_phone,
            status='ACTIVE'
        ).first()

        if agreement:
            # Agreement exists, create payment directly
            res = bkash.create_payment(
                agreement_id=agreement.agreement_id,
                amount=order.total_amount,
                merchant_invoice=str(order.id),
                callback_url=callback_url
            )
            return {
                "type": "PAYMENT",
                "bkashURL": res.get('bkashURL'),
                "paymentID": res.get('paymentID')
            }
        else:
            # No agreement, create one first
            res = bkash.create_agreement(
                payer_reference=customer_phone,
                callback_url=callback_url
            )
            return {
                "type": "AGREEMENT",
                "bkashURL": res.get('bkashURL'),
                "paymentID": res.get('paymentID')
            }

    def capture_bkash_callback(self, payment_id: str, status: str):
        """
        Handles the callback from bKash after customer approval.
        """
        bkash = BKashService(self.shop)
        
        if status == 'success':
            # Check if this was an agreement or a payment
            # bKash API distinguishes this by status code/response
            # For simplicity, we query bKash or try both
            
            # 1. Try Execute Agreement
            res = bkash.execute_agreement(payment_id)
            if res.get('statusCode') == '0000':
                # Agreement successful. Now we need to create the actual payment.
                # In a real flow, the customer might need to be redirected again or 
                # we auto-trigger the payment if possible.
                # But bKash usually requires execute_payment for the amount.
                return {"status": "AGREEMENT_EXECUTED", "data": res}

            # 2. Try Execute Payment
            res = bkash.execute_payment(payment_id)
            if res.get('statusCode') == '0000':
                # Payment successful. Update Order.
                self._finalize_order_payment(res.get('merchantInvoiceNumber'), res.get('trxID'), res)
                return {"status": "PAYMENT_COMPLETED", "data": res}
                
        return {"status": "FAILED", "paymentID": payment_id}

    def _finalize_order_payment(self, order_id: str, trx_id: str, gateway_response: dict):
        """
        Updates order status and records the transaction.
        """
        with transaction.atomic():
            order = Order.objects.get(id=order_id)
            order.status = OrderStatus.CONFIRMED
            order.save(update_fields=['status', 'updated_at'])
            
            # Record transition
            from orders.models import OrderTransitionLog
            OrderTransitionLog.objects.create(
                order=order,
                from_status=OrderStatus.AWAITING_PAYMENT,
                to_status=OrderStatus.CONFIRMED,
                reason="bKash Payment Completed",
                metadata={"trxID": trx_id, "response": gateway_response}
            )
            
            # Record transaction (if not already recorded by BKashService.execute_payment)
            # BKashService already creates PaymentTransaction in execute_payment
            pass
