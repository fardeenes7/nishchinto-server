from rest_framework import generics, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from shops.models import Shop, SubscriptionPlan, ShopMember
from django.db import transaction

class ShopCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    subdomain = serializers.CharField(max_length=100)

class ShopCreateView(generics.CreateAPIView):
    """
    Publicly accessible store creation for authenticated users.
    Waitlist system is removed.
    """
    permission_classes = [IsAuthenticated] # Must be logged in via Google
    serializer_class = ShopCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        subdomain = serializer.validated_data['subdomain'].lower()
        name = serializer.validated_data['name']
        user = request.user

        # 1. Check if user already owns a shop (Nishchinto is 1-shop-per-user for now)
        if ShopMember.objects.filter(user=user, role='OWNER').exists():
            return Response({'detail': 'You already own a shop.'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Check subdomain availability
        if Shop.objects.filter(subdomain=subdomain).exists():
            return Response({'detail': 'Subdomain already taken.'}, status=status.HTTP_400_BAD_REQUEST)

        from django.conf import settings
        if subdomain in settings.SUBDOMAIN_BLACKLIST:
             return Response({'detail': 'Subdomain is reserved.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # 3. Assign Default Free Plan
            free_plan, _ = SubscriptionPlan.objects.get_or_create(name='FREE')
            
            # 4. Create Shop
            shop = Shop.objects.create(
                name=name,
                subdomain=subdomain,
                plan=free_plan
            )
            
            # 5. Map Owner
            ShopMember.objects.create(
                user=user,
                shop=shop,
                role='OWNER'
            )
            
        return Response({
            'detail': 'Shop created successfully!', 
            'subdomain': subdomain,
            'shop_id': str(shop.id)
        }, status=status.HTTP_201_CREATED)
