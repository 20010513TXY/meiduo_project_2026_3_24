from django.urls import path
from apps.areas.views import AreasView, SubAreasView

urlpatterns = [
    path('areas/',AreasView.as_view()),
    path('areas/<pk>/',SubAreasView.as_view())
]
