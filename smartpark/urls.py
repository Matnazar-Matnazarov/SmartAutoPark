# urls.py
from django.urls import path
from .views import receive_image, LoginView, LogoutView, HomeView

urlpatterns = [
    path('receive-image/', receive_image),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('home/', HomeView.as_view(), name='home'),
]
