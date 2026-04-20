from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class WaitlistRedisThrottle(AnonRateThrottle):
    """
    Limits the waitlist POST endpoint to prevent spam.
    Configured dynamically. Fallback is 3 requests per hour per IP.
    Requires Redis cache backend to be functioning.
    """
    rate = '3/hour'


class SocialOAuthThrottle(UserRateThrottle):
    scope = "social_oauth"


class SocialPublishThrottle(UserRateThrottle):
    scope = "social_publish"
