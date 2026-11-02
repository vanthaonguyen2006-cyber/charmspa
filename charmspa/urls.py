from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/customer/', permanent=False)),
    path('admin/', admin.site.urls),
    path('feedback/', include('feedback.urls')),
    path('customer/', include('customers.urls')),
    path('home/', include('core.urls')),
    path('bookings/', include('bookings.urls')),
    path('accounts/', include('accounts.urls')),
    path('chatbot/', include('chatbot.urls')),
]

# Cho phép xem các tệp đã tải lên
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )