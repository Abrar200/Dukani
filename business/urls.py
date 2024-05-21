from django.urls import path
from . import views
from .views import BusinessRegistrationView

urlpatterns = [
    path('', views.home, name="home"),
    path('shop/', views.shop, name="shop"),
    path('community/', views.community, name="community"),
    path('community/?country=<int:country_id>', views.community, name='community'),
    path('events/', views.events, name='events'),
    path('create-event/', views.create_event, name='create_event'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('user/register-business', BusinessRegistrationView.as_view(), name="business_registration"),
    path('business/<slug:business_slug>/', views.BusinessDetailView.as_view(), name='business_detail'),
    path('business/<slug:business_slug>/product/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('business/<slug:business_slug>/product/<slug:product_slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('business/<slug:business_slug>/product/<slug:product_slug>/edit/', views.ProductEditView.as_view(), name='product_edit'),
    path('business/<slug:business_slug>/service/create/', views.ServiceCreateView.as_view(), name='service_create'),
    path('business/<slug:business_slug>/service/<slug:service_slug>/', views.ServiceDetailView.as_view(), name='service_detail'),
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/data/', views.CartView.as_view(), name='cart_data'),
    path('cart/update_quantity/', views.CartView.as_view(), name='update_quantity'),
    path('checkout/', views.checkout, name="checkout"),
    path('message/<slug:business_slug>/', views.message_seller, name='message_seller'),
    path('messages/', views.user_messages_view, name='user_messages'),
    path('messages/?business_slug=<slug:business_slug>', views.user_messages_view, name='user_messages'),
]