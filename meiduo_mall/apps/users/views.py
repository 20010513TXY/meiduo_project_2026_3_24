from django.shortcuts import render

# Create your views here.
from django.views import View
from .models import User
from django.http import JsonResponse


class UsernameCountView(View):
    # 用户名数量
    def get(self,request,username):
        count = User.objects.filter(username=username).count()
        return JsonResponse({'code':1,'errmsg':'ok','count':count})

class MobileCountView(View):
    # 手机号数量
    def get(self,request,mobile):
        count = User.objects.filter(mobile=mobile).count()
        return JsonResponse({'code':1,'errmsg':'ok','count':count})