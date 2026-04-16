import json
import logging
import re

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

# Create your views here.
from django.views import View
from django_redis import get_redis_connection

from .models import User, Address

from django.http import JsonResponse

from utils.views import LoginRequiredJSONMixin

from celery_tasks.email.tasks import send_verify_email
from apps.users.utils import check_email_verify_url

from meiduo_mall import settings
from apps.users.utils import generate_email_verify_url

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

class LogoutView(View):
    """用户登出"""
    def delete(self,request):
        """清空session"""
        logout(request)
        response = JsonResponse({'code':0,'errmsg':'退出登录成功'})
        response.delete_cookie('username')
        return response

class UserInfoView(LoginRequiredJSONMixin, View):
    """用户信息"""
    def get(self,request):
        info_data = {
            'username' : request.user.username,
            'mobile' : request.user.mobile,
            'email' : request.user.email,
            'email_active' : request.user.email_active
        }

        return JsonResponse({'code':0,'errmsg':'OK','info_data':info_data})

class EmailView(View):
    """保存邮箱"""
    def put(self,request):
        json_dict = json.loads(request.body.decode())
        email = json_dict.get('email')
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
            return JsonResponse({'code':400,'errmsg':'邮箱格式错误'})

        # User.objects.filter(id=request.user.id).update(email=email)
        # User.objects.filter(id=request.user.id).update(email_active=True)

        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            logging.info(e)
            return JsonResponse({'code':400,'errmsg':'保存邮箱失败'})

        subject = '美多商城邮箱验证'
        message = ''
        from_email = settings.EMAIL_FROM
        recipient_list = [email]

        token = generate_email_verify_url(request.user.id)

        verify_url = "http://www.meiduo.site:8080/success_verify_email.html?token=%s"%token
        html_message = '<p>尊敬的用户您好！</p>' \
                       '<p>感谢您使用美多商城。</p>' \
                       '<p>您的邮箱为：%s 。请点击此链接激活您的邮箱：</p>' \
                       '<p><a href="%s">%s<a></p>' % (email, verify_url, verify_url)

        send_verify_email.delay(subject, message, from_email, recipient_list, html_message)

        return JsonResponse({'code':0,'errmsg':'OK'})

class VerifyEmailView(View):
    """验证邮箱"""
    def put(self,request):
        token = request.GET.get('token')
        if not token:
            return JsonResponse({'code':400,'errmsg':'缺少token'})


        user = check_email_verify_url(token)
        if user is None:
            return JsonResponse({'code':400,'errmsg':'链接信息无效'})

        try:
            user = User.objects.get(id=user.id)
        except Exception as e:
            logging.info(e)
            return JsonResponse({'code':400,'errmsg':'用户信息获取失败'})

        try:
            user.email_active = True
            user.save()
            return JsonResponse({'code':0,'errmsg':'OK'})
        except Exception as e:
            logging.info(e)
            return JsonResponse({'code':400,'errmsg':'激活失败'})


class CreateAddressView(LoginRequiredJSONMixin, View):
    # LoginRequiredJSONMixin 是一个登录验证mixin，用于确保只有已登录用户才能访问该视图。
    """用户新增地址"""
    def post(self, request):
        count = request.user.addresses.count()
        if count >= 20:
            return JsonResponse({'code':400,'errmsg':'超过地址数量上限'})

        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # tel 和 email 可选
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return JsonResponse({'code':400,'errmsg':'缺少必传参数'})
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return JsonResponse({'code':400,'errmsg':'参数mobile有误'})
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$',tel):
                return JsonResponse({'code':400,'errmsg':'参数tel有误'})
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
                return JsonResponse({'code':400,'errmsg':'参数email有误'})

        try:
            address = Address.objects.create(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )

            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()

        except Exception as e:
            logging.info(e)
            return JsonResponse({'code':400,'errmsg':'新增地址失败'})

        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province': address.province.name,
            'city': address.city.name,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email
        }

        return JsonResponse({'code':0,'errmsg':'新增地址成功','address':address_dict})


class AddressView(LoginRequiredJSONMixin, View):
    """查看用户收货地址"""
    def get(self, request):
        addresses = request.user.addresses.filter(is_deleted=False)
        address_list = []
        for address in addresses:
            address_dict = {
                'id': address.id,
                'title': address.title,
                'receiver': address.receiver,
                'province': address.province.name,
                'city': address.city.name,
                'district': address.district.name,
                'place': address.place,
                'mobile': address.mobile,
                'tel': address.tel,
                'email': address.email
            }

            default_address = request.user.default_address
            if default_address.id == address.id:
                address_list.insert(0, address_dict)
            else:
                address_list.append(address_dict)

        default_address_id = request.user.default_address_id
        return JsonResponse({'code':0,'errmsg':'OK','addresses':address_list,'default_address_id':default_address_id})


class UpdateAddressView(LoginRequiredJSONMixin, View):
    """更新和删除用户收货地址"""
    def put(self, request, address_id):
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return JsonResponse({'code':400,'errmsg':'缺少必传参数'})

        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return JsonResponse({'code':400,'errmsg':'参数mobile有误'})
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$',tel):
                return JsonResponse({'code':400,'errmsg':'参数tel有误'})
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
                return JsonResponse({'code':400,'errmsg':'参数email有误'})

        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except Exception as e:
            logging.info(e)
            return JsonResponse({'code':400,'errmsg':'更新地址失败'})

        address = Address.objects.get(id=address_id)
        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province': address.province.name,
            'city': address.city.name,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email
        }
        return JsonResponse({'code':0,'errmsg':'更新地址成功','address':address_dict})

    def delete(self, request, address_id):
        # 先判断地址是不是默认地址，如果是默认地址，先将默认地址改为None，再删除地址；如果不是默认地址，直接删除地址
        try:
            address = Address.objects.get(id=address_id, user=request.user, is_deleted=False)
        except Address.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '地址不存在或无权限删除'})

        # 如果删除的是默认地址，清空用户的默认地址设置
        if request.user.default_address_id == address_id:
            request.user.default_address = None
            request.user.save()

        # 逻辑删除
        address.is_deleted = True
        address.save(update_fields=['is_deleted'])

        return JsonResponse({'code': 0, 'errmsg': '删除地址成功'})

