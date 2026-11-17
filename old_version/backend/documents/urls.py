from django.urls import path
from . import views
from . import review_views
from . import templates

urlpatterns = [
    path('templates/', templates.catalog),
    path('templates/<str:key>/', templates.prepare),
    path('validation/<str:kind>/<int:pk>/', review_views.validation),
    path('validation/<str:kind>/<int:pk>/export/<str:document>/', review_views.export),
    path("folders/", views.folders),
    path("folders/<int:pk>/", views.folders),
    path("items/", views.items),
    path("items/<int:pk>/", views.item),
    path("items/<int:pk>/upload/", views.upload),
    path("items/<int:pk>/download/", views.download),
    path("versions/<int:version>/download/", views.download),
]
