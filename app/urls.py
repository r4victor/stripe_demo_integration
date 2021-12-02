from django.urls import path

from . import views


urlpatterns = [
    path('create-subscription', views.create_subscription),
    path('payment-webhook', views.payment_webhook),
    path('checkout/', views.checkout, name='checkout'),
    path('', views.home, name='home')
]