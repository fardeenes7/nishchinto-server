"""
billing/services/refund.py

Service for handling partial and full refunds.
Integrates with payment gateways (bKash Tokenized) as per §3 of business rules.
"""

import logging
from django.db import transaction
from billing.models import PaymentTransaction, PaymentGatewayConfig, RefundRecord
from billing.services.bkash import BKashService
from orders.models import Order, OrderRefundEvent, OrderRefundStatus

logger = logging.getLogger(__name__)

class RefundService:
    """
    Manages refund operations across gateways.
    """

    def __init__(self, shop_id):
        from shops.models import Shop
        self.shop = Shop.objects.get(id=shop_id)

    def initiate_refund(self, order_id: str, amount: float, reason: str, actor_user):
        """
        Processes a refund for a given order.
        Checks for a completed transaction first.
        """
        # 1. Find the successful transaction
        transaction_record = PaymentTransaction.objects.filter(
            order_id=order_id,
            status__in=[PaymentTransaction.STATUS_COMPLETED, PaymentTransaction.STATUS_PARTIALLY_REFUNDED]
        ).first()

        if not transaction_record:
            raise ValueError("No eligible completed transaction found for this order.")

        if amount > transaction_record.amount:
            raise ValueError("Refund amount exceeds the original transaction amount.")

        # 2. Trigger gateway-specific refund
        if transaction_record.gateway == PaymentGatewayConfig.GATEWAY_BKASH:
            return self._refund_bkash(transaction_record, amount, reason, actor_user)
        else:
            raise ValueError(f"Refunds not supported for gateway {transaction_record.gateway} yet.")

    def _refund_bkash(self, transaction_record: PaymentTransaction, amount: float, reason: str, actor_user):
        """
        Calls bKash Partial Refund API.
        """
        bkash = BKashService(self.shop)
        
        # We need the paymentID from the original gateway response
        payment_id = transaction_record.gateway_response.get('paymentID')
        if not payment_id:
            raise ValueError("Original paymentID missing from transaction record.")

        res = bkash.refund(
            trx_id=transaction_record.external_transaction_id,
            payment_id=payment_id,
            amount=amount,
            reason=reason
        )

        if res.get('statusCode') == '0000':
            # 3. Create OrderRefundEvent for auditing
            with transaction.atomic():
                OrderRefundEvent.objects.create(
                    order_id=transaction_record.order_id,
                    shop=self.shop,
                    amount=amount,
                    status=OrderRefundStatus.COMPLETED,
                    reason=reason,
                    actor_user=actor_user,
                    metadata={"res": res}
                )
                
                # Update order status if it was a full refund
                # (Business logic check: total_refunded >= order_total)
                pass 
                
            return {"status": "SUCCESS", "refundTrxID": res.get('refundTrxID')}
        
        raise Exception(f"bKash Refund Failed: {res.get('statusMessage')}")
