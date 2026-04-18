from rest_framework.throttling import AnonRateThrottle

class WaitlistRedisThrottle(AnonRateThrottle):
    """
    Limits the waitlist POST endpoint to prevent spam.
    Configured dynamically. Fallback is 3 requests per hour per IP.
    Requires Redis cache backend to be functioning.
    """
    rate = '3/hour'
