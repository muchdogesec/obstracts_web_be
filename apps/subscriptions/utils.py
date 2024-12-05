from apps.utils.billing import get_stripe_module

def close_customer_and_subscriptions(customer_id):
    stripe = get_stripe_module()
    customer = stripe.Customer.retrieve(customer_id)
    
    subscriptions = stripe.Subscription.list(customer=customer_id)

    if subscriptions.data:
        for subscription in subscriptions.auto_paging_iter():
            stripe.Subscription.delete(subscription.id)
    stripe.Customer.delete(customer_id)
