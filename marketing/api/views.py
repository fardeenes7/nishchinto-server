from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from marketing.models import WaitlistEntry
from marketing.serializers import WaitlistEntrySerializer
from .throttles import WaitlistRedisThrottle
from marketing.tasks import send_waitlist_invite_email
import uuid

class WaitlistCreateView(generics.CreateAPIView):
    """
    Unauthenticated endpoint for users to join the waitlist.
    """
    queryset = WaitlistEntry.objects.all()
    serializer_class = WaitlistEntrySerializer
    permission_classes = [AllowAny]
    throttle_classes = [WaitlistRedisThrottle]

class AdminWaitlistView(generics.ListAPIView):
    """
    Admin-only read access to the waitlist queue.
    """
    queryset = WaitlistEntry.objects.all().order_by('-created_at')
    serializer_class = WaitlistEntrySerializer
    # In Django REST Framework, IsAdminUser natively checks `is_staff=True`, perfectly matching our strict rules!
    permission_classes = [IsAdminUser]

class AdminWaitlistApproveView(generics.GenericAPIView):
    """
    Admin action to approve a waiting user and generate an invite link.
    """
    queryset = WaitlistEntry.objects.all()
    # In Django REST Framework, IsAdminUser natively checks `is_staff=True`, perfectly matching our strict rules!
    permission_classes = [IsAdminUser]

    def post(self, request, pk, *args, **kwargs):
        entry = self.get_object()
        
        if entry.status == 'APPROVED':
            return Response({'detail': 'Already approved.'}, status=status.HTTP_400_BAD_REQUEST)
            
        entry.status = 'APPROVED'
        entry.invite_token = uuid.uuid4()
        entry.save()
        
        # Dispatch Celery task to send invite
        send_waitlist_invite_email.delay(entry.email, str(entry.invite_token))
        
        return Response({'detail': 'Approved successfully', 'token': entry.invite_token})

