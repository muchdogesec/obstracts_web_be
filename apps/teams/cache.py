from django.core.cache import cache


PRODUCT_METADATA_ALLOWED_API_KEY_CACHE_KEY = 'team.product_metadata_allowed_api_key'

def _get_product_metadata_allowed_api_cache_key(product_id):
    return f'{PRODUCT_METADATA_ALLOWED_API_KEY_CACHE_KEY}:{product_id}'
def save_product_allowed_feeds_value(product_id, allowed_api_access):
    cache.set(_get_product_metadata_allowed_api_cache_key(product_id), allowed_api_access, timeout=60)

def get_product_allowed_feeds_value(product_id):
    return cache.get(_get_product_metadata_allowed_api_cache_key(product_id))
