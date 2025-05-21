from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Commenting out the default Django admin path to prevent redirect to Django admin panel
    # path('admin/', admin.site.urls),
    path('', include('frontend.urls')),
]
