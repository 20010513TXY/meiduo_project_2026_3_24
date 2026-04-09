import re

from django.contrib.auth import login
from django.db import DatabaseError
from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from QQLoginTool.QQtool import OAuthQQ
from django_redis import get_redis_connection

from meiduo_mall import settings
from django.views import View

from apps.oauth.models import OAuthQQUser
from apps.users.models import User
import json

from apps.oauth.utils import check_access_token


#
# oauth =OAuthQQ(client_id=settings.QQ_CLIENT_ID,client_secret=settings.QQ_CLIENT_SECRET,
#         redirect_uri=settings.QQ_REDIRECT_URI,state=next)
#
# login_url =  oauth.get_qq_url()
#
# access_token = oauth.get_access_token(code)
#
# open_id = oauth.get_open_id(access_token)

class QQAuthURLView(View):
    """提供QQ登录扫码页面"""
    def get(self,request):
        # next为用户点击登录时，从哪个页面跳转回来
        next = request.GET.get('next')
        # 创建工具对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next)
        # 生成 QQ 登录扫码页面
        login_url = oauth.get_qq_url()
        return JsonResponse({'code':0,'errmsg':'ok','login_url':login_url})

class OAuthQQView(View):
    """用户扫码登录后，QQ返回给的页面"""
    def get(self,request):
        code = request.GET.get('code')
        if code is None:
            return JsonResponse({'code':400,'errmsg':'code参数错误'})
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI)

        access_token = oauth.get_access_token(code)
        openid = oauth.get_open_id(access_token)
        try:
            qq_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 如果qq_user不存在，则创建用户
            # 创建用户
            # 获取用户信息
            access_token = oauth.generate_access_token({'openid':openid})
            return JsonResponse({'code':300,'errmsg':'ok','access_token':access_token})
        else:
            # 如果qq_user存在，则直接登录用户
            # 创建用户
            # 获取用户信息
            user = qq_user.user
            login(request,user)
            response = JsonResponse({'code':0,'errmsg':'ok'})
            response.set_cookie('username',user.username,max_age=14*24*3600,path='/',secure=False,samesite='None')
            return response


    def post(self,request):
        """用户扫码登录后，绑定用户"""
        data = json.loads(request.body.decode())
        mobile = data.get('mobile')
        password = data.get('password')
        sms_code = data.get('sms_code')
        access_token = data.get('access_token')

        if not all([mobile,password,sms_code,access_token]):
            return JsonResponse({'code':400,'errmsg':'缺少必传参数'})

        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return JsonResponse({'code':400,'errmsg':'手机号格式错误'})

        if not re.match(r'^[0-9A-Za-z]{3,20}$',password):
            return JsonResponse({'code':400,'errmsg':'密码格式错误'})

        redis_conn = get_redis_connection('code')
        sms_code_redis = redis_conn.get('sms:%s'%mobile)
        if sms_code_redis is None:
            return JsonResponse({'code':400,'errmsg':'短信验证码已过期'})
        if sms_code != sms_code_redis.decode():
            return JsonResponse({'code':400,'errmsg':'短信验证码错误'})

        openid = check_access_token(access_token)
        if openid is None:
            return JsonResponse({'code':400,'errmsg':'openid已过期'})
        try:
            user = User.objects.get(openid=openid)
        except User.DoesNotExist:
            user = User.objects.create(username=mobile,
                                mobile=mobile,
                                password=password)
        else:
            if not user.check_password(password):
                return JsonResponse({'code':400,'errmsg':'密码错误'})
        try:
            OAuthQQUser.objects.create(user=user,openid=openid)
        except DatabaseError:
            return JsonResponse({'code':400,'errmsg':'往数据库添加数据出错'})

        login(request,user)
        response = JsonResponse({'code':0,'errmsg':'ok'})
        response.set_cookie('username',user.username,max_age=14*24*3600,path='/',secure=False,samesite='None')
        return response





