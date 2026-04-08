import json
import re

from django.contrib.auth import authenticate, login
from django.shortcuts import render

# Create your views here.
from django.views import View
from django_redis import get_redis_connection

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
        if not all([username,password,password2,mobile,sms_code,allow]):
            return JsonResponse({'code':400,'errmsg':'缺少必要参数'})
        # 3.2 用户名满足规则，且不能重复
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$',username):
            return JsonResponse({'code':400,'errmsg':'用户名格式错误'})
        # 3.3 密码要满足规则
        if not re.match(r'^[0-9A-Za-z]{3,20}$',password):
            return JsonResponse({'code':400,'errmsg':'密码格式错误'})
        # 3.4 密码和确认密码要一致
        if password != password2:
            return JsonResponse({'code':400,'errmsg':'密码不一致'})
        # 3.5 手机号满足规则，且不能重复
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return JsonResponse({'code':400,'errmsg':'手机号格式错误'})
        # 3.6 短信验证码 要和redis中保存的验证码一致
        redis_conn = get_redis_connection('verify_code')


        sms_code_server = redis_conn.get('sms_%s'%mobile)
        if sms_code_server is None:
            return JsonResponse({'code':400,'errmsg':'短信验证码已过期'})
        if sms_code != sms_code_server.decode():
            return JsonResponse({'code':400,'errmsg':'短信验证码错误'})

        # 3.7 同意协议
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
        response = JsonResponse({'code': 0, 'errmsg': '注册成功'})
        response.set_cookie('username', user.username, max_age=15*24*3600, path='/')
        return response


class LoginView(View):
    """用户登录"""
    def post(self,request):

        request_data = request.body
        json_dict = json.loads(request_data.decode())
        username = json_dict.get('username')
        password = json_dict.get('password')
        remember = json_dict.get('remember')
        if not all([username,password]):
            return JsonResponse({'code':400,'errmsg':'缺少必要参数'})

        # 根据输入格式动态切换登录字段：
        # 如果输入的是手机号格式，就让 authenticate() 用手机号字段查询用户；否则用用户名字段查询。
        # 这样实现了同时支持用户名和手机号两种方式登录。
        # User.USERNAME_FIELD 告诉 Django 用哪个字段作为"用户名"来查询。
        # 输入 13812345678 → 设置 USERNAME_FIELD = 'mobile' → authenticate() 实际执行 User.objects.get(mobile='13812345678')
        # 输入 zhangsan → 设置 USERNAME_FIELD = 'username' → authenticate() 实际执行 User.objects.get(username='zhangsan')
        # 所以虽然代码都写的是 authenticate(username=xxx)，但实际查询的字段会根据 USERNAME_FIELD 动态变化。
        if re.match(r'^1[3-9]\d{9}$',username):
            User.USERNAME_FIELD = 'mobile'
        else:
            User.USERNAME_FIELD = 'username'

        # authenticate() 是 Django 封装的认证方法，内部自动从数据库查询用户并验证加密密码。
        # 比手动查询更安全简洁，避免了直接处理密码哈希的复杂性和风险。
        user = authenticate(username=username,password=password)
        if user is None:
            return JsonResponse({'code':400,'errmsg':'用户名或密码错误'})
        # login(request, user) 会在服务器创建 session 并在浏览器设置 cookie，记录用户已登录状态。
        # 之后 Django 能通过 session 自动识别用户，无需重复输入密码。
        login(request,user)
        # 控制登录状态的有效期：
        # set_expiry(None) 表示 session 长期有效（默认2周），实现"记住我"功能
        # set_expiry(0) 表示关闭浏览器后 session 立即失效
        if remember:
            request.session.set_expiry(None)
        else:
            request.session.set_expiry(0)

        response = JsonResponse({'code':0,'errmsg':'登录成功'})
        # 用户名写入cookie，有效期15天
        response.set_cookie('username',user.username,max_age=15*24*3600, path='/',samesite='None',secure=False)
        return response
