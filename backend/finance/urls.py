from django.urls import path
from . import views
from . import advanced
from . import banking
from . import cycle_views, funding_views, residents, notices
urlpatterns=[
    path('resident-context/', residents.context),
    path('residents/', residents.owners),
    path('residents/<int:pk>/', residents.owners),
    path('my-resident/', residents.personal),
    path('resident-payment/', residents.payment),
    path('charge-calls/', residents.charges),
    path('charge-calls/<str:action>/', residents.charges),
    path('call-notices/<int:pk>/', notices.call_notices),
    path('my-notices/', notices.my_notices),
    path('notice-download/<int:pk>/', notices.download),
    path('lot-history/<int:pk>/', residents.lot_history),
path('funding/<str:resource>/',funding_views.funding),path('cycle/<str:resource>/',cycle_views.cycle),path('cycle/<str:resource>/<int:pk>/',cycle_views.cycle),path('banks/',banking.banks),path('banks/<int:pk>/',banking.banks),path('banks/<int:pk>/default/',banking.default_bank),path('bank-transfers/',banking.transfers),path("manage/<str:resource>/",advanced.manage),path("manage/<str:resource>/<int:pk>/",advanced.manage),path("operations/<str:resource>/<int:pk>/",advanced.operations),path("reporting/<str:kind>/",advanced.reports),path("<str:resource>/",views.collection),path("<str:resource>/<int:pk>/<str:operation>/",views.action)]
