import json

from django.contrib.auth.models import User
from django.db import models

# Create your models here.

class SubscriptionData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=100)
    stripe_subscription_id = models.CharField(max_length=100)
    stripe_subscription_data = models.TextField()

    def __str__(self) -> str:
        return json.dumps({
            'Stripe Customer': self.stripe_customer_id,
            'Stripe Subscription': self.stripe_subscription_id,
            'Data': json.loads(self.stripe_subscription_data),
        }, indent=4)
