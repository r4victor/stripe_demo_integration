import json
import os
import uuid

from django.contrib.auth.models import User

from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

import stripe

from .models import SubscriptionData


stripe.api_key = os.environ['STRIPE_SECRET_KEY']


def home(request: HttpRequest) -> HttpResponse:
    user = _get_user_from_session(request)
    context = {
        'subscription_data': _get_subscription_data(user)
    }
    return render(request, 'app/home.html', context)


def _get_subscription_data(user: User) -> SubscriptionData:
    try:
        return SubscriptionData.objects.get(user=user)
    except SubscriptionData.DoesNotExist:
        return None


def checkout(request: HttpRequest) -> HttpResponse:
    user = _get_user_from_session(request)
    return render(request, 'app/checkout.html')


def _get_user_from_session(request: HttpRequest):
    user_id = request.session.get('user_id')
    if user_id is None:
        user = User.objects.create(username=str(uuid.uuid4()))
        request.session['user_id'] = user.id
        return user
    return User.objects.get(id=user_id)


@csrf_exempt
def create_subscription(request: HttpRequest) -> JsonResponse:
    user_id = request.session['user_id']
    user = User.objects.get(id=user_id)
    try:
        subscription_data = SubscriptionData.objects.get(user=user)
    except SubscriptionData.DoesNotExist:
        customer = stripe.Customer.create(name=f'Customer #{user.id}')
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{
                'price': 'price_1K1oXUB4pagOZetqRfXAKtCW',
            }],
            payment_behavior='default_incomplete',
            expand=['latest_invoice.payment_intent'],
        )
        subscription_data = SubscriptionData.objects.create(
            user=user, stripe_customer_id=customer.id,
            stripe_subscription_id=subscription.id,
            stripe_subscription_data=subscription
        )
    else:
        subscription = stripe.Subscription.retrieve(
            subscription_data.stripe_subscription_id,
            expand=['latest_invoice.payment_intent']
        )

    return JsonResponse({'client_secret': subscription.latest_invoice.payment_intent.client_secret})


@csrf_exempt
def payment_webhook(request: HttpRequest) -> JsonResponse:
    try:
        event = stripe.Event.construct_from(
            json.loads(request.body), stripe.api_key
        )
    except ValueError:
        return HttpResponse(status=400)

    data_object = event['data']['object']

    if event['type'] == 'invoice.payment_succeeded':
        if data_object['billing_reason'] == 'subscription_create':
            print(data_object)
            # The subscription automatically activates after successful payment
            # Set the payment method used to pay the first invoice
            # as the default payment method for that subscription
            subscription_id = data_object['subscription']
            payment_intent_id = data_object['payment_intent']
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            stripe.Subscription.modify(
              subscription_id,
              default_payment_method=payment_intent.payment_method
            )

            print("Default payment method set for subscription:" + payment_intent.payment_method)

            # Update subscription data (e.g. status)
            subscription = stripe.Subscription.retrieve(subscription_id)
            subscription_data = SubscriptionData.objects.get(stripe_subscription_id=subscription_id)
            subscription_data.stripe_subscription_data = subscription
            subscription_data.save()


    return JsonResponse({'success': True})