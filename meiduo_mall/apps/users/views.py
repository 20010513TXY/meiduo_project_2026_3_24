import json
import re

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


class RegisterView(View):
    """用户注册"""
    def post(self,request):
        # 1、接受请求 POST ---------JSON
        json_bytes = request.body
        json_str = json_bytes.decode()
        json_dict = json.loads(json_str)

        # 2、获取数据
        username = json_dict.get('username')
        password = json_dict.get('password')
        password2 = json_dict.get('password2')
        mobile = json_dict.get('mobile')
        sms_code = json_dict.get('sms_code')
        allow = json_dict.get('allow')

        # 3、验证数据
        # 3.1 用户名 · 密码 · 确认密码 · 手机号 · 同意协议 不能缺失
        if not all([username,password,password2,mobile,allow]):
            return JsonResponse({'code':400,'errmsg':'缺少必要参数'})
        # 3.2 用户名满足规则，且不能重复
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$',username):
            return JsonResponse({'code':400,'errmsg':'用户名格式错误'})
        # 3.3 密码要满足规则
        if not re.match(r'^[0-9A-Za-z]{8,20}$',password):
            return JsonResponse({'code':400,'errmsg':'密码格式错误'})
        # 3.4 密码和确认密码要一致
        if password != password2:
            return JsonResponse({'code':400,'errmsg':'密码不一致'})
        # 3.5 手机号满足规则，且不能重复
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return JsonResponse({'code':400,'errmsg':'手机号格式错误'})
        # 3.6 同意协议
        if allow != True:
            return JsonResponse({'code':400,'errmsg':'请勾选协议'})
        # 4、存入数据库
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except Exception as e:
            return JsonResponse({'code':400,'errmsg':'注册失败'})

        # 实现状态保持
        from django.contrib.auth import login
        login(request,user)

        # 5、返回响应
        return JsonResponse({'code': 0, 'errmsg': '注册成功'})
