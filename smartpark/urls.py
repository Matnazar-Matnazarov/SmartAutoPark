# urls.py
from django.urls import path
from .views import receive_entry, receive_exit, LoginView, LogoutView, HomeView

urlpatterns = [
    path('receive-entry/', receive_entry),
    path('receive-exit/', receive_exit),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('home/', HomeView.as_view(), name='home'),
]
