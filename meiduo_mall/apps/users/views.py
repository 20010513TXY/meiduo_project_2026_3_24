from django.shortcuts import render

# Create your views here.
from django.views import View
from .models import User
from django.http import JsonResponse


class UsernameCountView(View):
    def get(self,request,username):
        count = User.objects.filter(username=username).count()
        return JsonResponse({'code':1,'errmsg':'ok','count':count})

