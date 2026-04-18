from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from marketing.models import WaitlistEntry
from users.models import User
from shops.models import Shop, SubscriptionPlan
from django.db import transaction

class ShopClaimView(generics.GenericAPIView):
    """
    Step 1 of Merchant Onboarding.
    User provides their invite token, desired subdomain, and password.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        token = request.data.get('token')
        subdomain = request.data.get('subdomain')
        password = request.data.get('password')
        
        if not all([token, subdomain, password]):
            return Response({'detail': 'Missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            entry = WaitlistEntry.objects.get(invite_token=token, status='APPROVED')
        except WaitlistEntry.DoesNotExist:
            return Response({'detail': 'Invalid or expired invite token.'}, status=status.HTTP_404_NOT_FOUND)

        # Check subdomain availability
        if Shop.objects.filter(subdomain=subdomain).exists():
            return Response({'detail': 'Subdomain already taken.'}, status=status.HTTP_400_BAD_REQUEST)

        from django.conf import settings
        if subdomain.lower() in settings.SUBDOMAIN_BLACKLIST:
             return Response({'detail': 'Subdomain is reserved.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # 1. Create User
            user = User.objects.create_user(
                email=entry.email,
                password=password
            )
            
            # 2. Assign Default Free Plan (or map from waitlist if needed)
            free_plan, _ = SubscriptionPlan.objects.get_or_create(name='FREE')
            
            # 3. Create Shop
            shop = Shop.objects.create(
                name=entry.survey_data.get('business_name', 'My New Shop'),
                subdomain=subdomain.lower(),
                plan=free_plan
            )
            
            # 4. Map Owner
            from shops.models import ShopMember
            ShopMember.objects.create(
                user=user,
                shop=shop,
                role='OWNER'
            )
            
            # 5. Mark entry as processed (optionally delete or change status)
            entry.status = 'CLAIMED' # Need to add this choice if not present
            entry.save()

        return Response({'detail': 'Shop claimed successfully! You can now login.'}, status=status.HTTP_201_CREATED)
