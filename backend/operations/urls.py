from django.urls import path
from . import views
from . import partners
from . import statements
urlpatterns=[path('cases/',views.cases),path('cases/<int:pk>/',views.case),path('cases/<int:pk>/quotes/',views.quotes),
 path('quotes/<int:pk>/select/',views.select_quote),path('reminders/',views.reminders),path('reminders/<int:pk>/',views.reminder),
 path('options/',views.options),path('metrics/',views.metrics),path('my-account/',statements.personal_account),
 path('my-account/export/',statements.export),
 path('suppliers/',partners.partners,{'resource':'suppliers'}),path('suppliers/<int:pk>/',partners.partners,{'resource':'suppliers'}),
 path('contracts/',partners.partners,{'resource':'contracts'}),path('contracts/<int:pk>/',partners.partners,{'resource':'contracts'}),
 path('certificates/',partners.partners,{'resource':'certificates'}),path('certificates/<int:pk>/',partners.partners,{'resource':'certificates'}),
 path('notices/',partners.notices),path('notices/<int:pk>/',partners.notice)]
