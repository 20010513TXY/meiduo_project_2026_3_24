from django.urls import path
from apps.oauth.views import QQAuthURLView, OAuthQQView

urlpatterns = [
    path('qq/authorization',QQAuthURLView.as_view()),
    path('oauth_callback/',OAuthQQView.as_view()),
]