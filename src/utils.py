import time
import random
import logging

logger = logging.getLogger(__name__)

def call_with_backoff(func, *args, max_retries=5, **kwargs):
    """
    Wraps API calls in an exponential backoff loop to handle transient
    server errors (like 503 Unavailable) and rate limits (429 Resource Exhausted).
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_str = str(e)
            # Identify typical transient error messages/status codes
            is_transient = any(
                indicator in err_str 
                for indicator in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "high demand", "Rate limit"]
            )
            
            if not is_transient or attempt == max_retries - 1:
                logger.error(f"API call failed after {attempt + 1} attempts: {e}")
                raise e
            
            # Exponential backoff delay calculation: (2^attempt) + jitter
            sleep_time = (2 ** attempt) + random.uniform(0.1, 1.0)
            logger.warning(
                f"Transient API error encountered ({e}). "
                f"Retrying in {sleep_time:.2f} seconds (Attempt {attempt + 1}/{max_retries})..."
            )
            time.sleep(sleep_time)
