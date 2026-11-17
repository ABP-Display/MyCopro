from django.urls import path
from copro import views

urlpatterns = [
    path('api/ag/electorate/',views.electorate),path('api/ag/tools/<str:kind>/',views.tools),
    path('api/health/',views.health),path('api/session/',views.session),
    path('api/login/',views.login),path('api/logout/',views.logout),path('api/password/',views.password),
    path('api/state/',views.state),path('api/owners/',views.owners),path('api/owners/<int:pk>/',views.owners),
    path('api/lots/',views.lots),path('api/lots/<int:pk>/',views.lots),
    path('api/banks/',views.banks),path('api/banks/<int:pk>/',views.banks),
    path('api/calls/<str:action>/',views.calls),path('api/payments/',views.payments),
    path('api/payments/<int:pk>/<str:action>/',views.payments),path('api/movements/',views.movements),
    path('api/posts/',views.posts),path('api/posts/<int:pk>/',views.posts),path('api/attachments/<int:pk>/',views.download),
    path('api/administration/<str:resource>/',views.administration),
]
