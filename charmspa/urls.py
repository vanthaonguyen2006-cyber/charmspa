
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/customer/', permanent=False)),
    path('admin/', admin.site.urls),
    path('notifications/', include('notifications.urls')),
    path('feedback/', include('feedback.urls')),
    path('customer/', include('customers.urls')),
    path('home/', include('core.urls')),
    path('bookings/', include('bookings.urls')),
    path('accounts/', include('accounts.urls')),
    path('core/', include('core.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('', include('services.urls')),
]
