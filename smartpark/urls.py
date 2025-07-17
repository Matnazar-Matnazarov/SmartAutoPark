# urls.py
from django.urls import path
from .views import (
    receive_entry, receive_exit, LoginView, LogoutView, HomeView,
    get_statistics, get_vehicle_entries, mark_as_paid, add_car, block_car
)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='home/', permanent=True)),
    path('receive-entry/', receive_entry),
    path('receive-exit/', receive_exit),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('home/', HomeView.as_view(), name='home'),
    
    # New API endpoints
    path('api/statistics/', get_statistics, name='get_statistics'),
    path('api/vehicle-entries/', get_vehicle_entries, name='get_vehicle_entries'),
    path('api/mark-paid/', mark_as_paid, name='mark_as_paid'),
    path('api/add-car/', add_car, name='add_car'),
    path('api/block-car/', block_car, name='block_car'),
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)+staticfiles_urlpatterns()
