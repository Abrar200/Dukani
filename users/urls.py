from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.user_register_view, name='register'),
    path('login/', views.user_login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/<str:username>', views.profile, name='profile'),
]