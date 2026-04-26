from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action

from analytics.selectors import (
    get_shop_sales_metrics, 
    get_top_customers_by_ltv, 
    get_cohort_retention_data
)
from analytics.api.serializers import (
    ShopSalesMetricsSerializer, 
    CustomerLTVSerializer, 
    CohortDataSerializer
)

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def sales(self, request):
        shop_id = request.tenant_id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        metrics = get_shop_sales_metrics(
            shop_id=shop_id, 
            start_date=start_date, 
            end_date=end_date
        )
        serializer = ShopSalesMetricsSerializer(metrics, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_customers(self, request):
        tenant_id = request.tenant_id
        limit = int(request.query_params.get('limit', 10))
        
        customers = get_top_customers_by_ltv(tenant_id=tenant_id, limit=limit)
        serializer = CustomerLTVSerializer(customers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def cohorts(self, request):
        tenant_id = request.tenant_id
        data = get_cohort_retention_data(tenant_id=tenant_id)
        serializer = CohortDataSerializer(data, many=True)
        return Response(serializer.data)
