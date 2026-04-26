from django.db import transaction
from django.db.models import F
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from accounting.api.serializers import AdminPayoutActionSerializer, AdminPayoutSerializer
from accounting.models import LedgerEntry, PlatformBalance, Payout


class AdminSettlementListView(generics.ListAPIView):
    queryset = Payout.objects.select_related('shop').order_by('-created_at')
    serializer_class = AdminPayoutSerializer
    permission_classes = [IsAdminUser]


class AdminSettlementApproveView(generics.GenericAPIView):
    queryset = Payout.objects.select_related('shop').all()
    serializer_class = AdminPayoutActionSerializer
    permission_classes = [IsAdminUser]

    def post(self, request, pk, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            payout = self.get_queryset().select_for_update().get(pk=pk)
            if payout.status != Payout.STATUS_PENDING:
                return Response(
                    {'detail': 'Only pending payouts can be approved.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payout.status = Payout.STATUS_PROCESSING
            payout.admin_note = serializer.validated_data.get('admin_note', '')
            payout.save(update_fields=['status', 'admin_note', 'updated_at'])

        return Response(AdminPayoutSerializer(payout).data, status=status.HTTP_200_OK)


class AdminSettlementRejectView(generics.GenericAPIView):
    queryset = Payout.objects.select_related('shop').all()
    serializer_class = AdminPayoutActionSerializer
    permission_classes = [IsAdminUser]

    def post(self, request, pk, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            payout = self.get_queryset().select_for_update().get(pk=pk)
            if payout.status != Payout.STATUS_PENDING:
                return Response(
                    {'detail': 'Only pending payouts can be rejected.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            balance, _ = PlatformBalance.objects.select_for_update().get_or_create(
                shop=payout.shop,
                defaults={'tenant_id': payout.shop_id},
            )

            balance.current_balance = F('current_balance') + payout.amount
            balance.total_withdrawn = F('total_withdrawn') - payout.amount
            balance.save(update_fields=['current_balance', 'total_withdrawn', 'updated_at'])

            payout.status = Payout.STATUS_FAILED
            payout.admin_note = serializer.validated_data.get('admin_note', '')
            payout.save(update_fields=['status', 'admin_note', 'updated_at'])

            LedgerEntry.objects.create(
                shop_id=payout.shop_id,
                tenant_id=payout.shop_id,
                entry_type=LedgerEntry.ENTRY_TYPE_ADJUSTMENT,
                amount=payout.amount,
                description=f'Payout rejection reversal: {payout.id}',
                payout=payout,
            )

        return Response(AdminPayoutSerializer(payout).data, status=status.HTTP_200_OK)
