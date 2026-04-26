from fraud.models import GlobalFraudPool, FraudConfig
import hashlib

def check_customer_risk(shop, phone_number):
    """
    Checks the global fraud pool for a phone number.
    Returns a risk summary.
    """
    if not phone_number:
        return {"risk_score": 0, "is_high_risk": False, "reports_count": 0}

    normalized_phone = "".join(filter(str.isdigit, phone_number))
    phone_hash = hashlib.sha256(normalized_phone.encode()).hexdigest()
    
    config, _ = FraudConfig.objects.get_or_create(shop=shop)
    
    # Opt-in check: You must contribute to see the global data
    if not config.opt_in_pooling:
        return {
            "risk_score": 0, 
            "is_high_risk": False, 
            "reports_count": 0,
            "message": "Opt-in to fraud pooling to see community data."
        }

    try:
        pool = GlobalFraudPool.objects.get(phone_hash=phone_hash)
        total_reports = pool.rto_count + pool.fake_order_count + pool.harassment_count + pool.unpaid_count
        
        # High risk if RTOs exceed merchant's defined threshold
        is_high_risk = pool.rto_count >= config.rto_threshold
        
        return {
            "risk_score": total_reports,
            "is_high_risk": is_high_risk,
            "reports_count": total_reports,
            "details": {
                "rto": pool.rto_count,
                "fake_order": pool.fake_order_count,
                "harassment": pool.harassment_count,
                "unpaid": pool.unpaid_count
            }
        }
    except GlobalFraudPool.DoesNotExist:
        return {"risk_score": 0, "is_high_risk": False, "reports_count": 0}
