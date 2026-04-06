import logging
import random

from django.shortcuts import render
from django.views import View
from libs.captcha.captcha import captcha
from django.http import HttpResponse, JsonResponse
from django_redis import get_redis_connection

from libs.yuntongxun.sms import CCP


# Create your views here.
class ImageCodeView(View):
    """图片验证码"""
    def get(self,request,uuid):
        text,image = captcha.generate_captcha()
        get_conn = get_redis_connection('code')
        get_conn.setex('img_%s'%uuid,300,text)
        return HttpResponse(image,content_type='image/jpeg')


class SMSCodeView(View):
    """短信验证码"""
    def get(self,request,mobile):
        # 请求： 接受请求，获取请求参数（手机号、图形验证码、UUID）
        # 业务逻辑：验证参数：图形验证码是否和redis中一致，生成短信验证码，发送短信，保存短信验证码到redis中
        # 响应： 响应结果
        # 步骤：
        # 1、获取请求参数 '/sms_codes/' + this.mobile + '/' + '?image_code=' + this.image_code + '&image_code_id=' + this.image_code_id
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        # 2、验证参数
        if not all([image_code_client,uuid]):
            return JsonResponse({'code':400,'errmsg':'缺少必要参数'})

        # 3、验证图片验证码
        redis_conn = get_redis_connection('code')
        image_code_server = redis_conn.get('img_%s'%uuid)
        if image_code_server is None:
            return JsonResponse({'code':400,'errmsg':'图片验证码已过期'})
        # 删除图形验证码：一次性使用，防止验证码被重复利用（重放攻击），后端在验证成功后会立刻从 Redis 中将其删除。这样即使黑客截获了刚才的请求包，也无法再次使用。
        try:
            redis_conn.delete('img_%s'%uuid)
        except Exception as e:
            logging.error(e)
            return JsonResponse({'code':400,'errmsg':'删除图片验证码失败'})
        # 对比图形验证码
        image_code_server = image_code_server.decode()
        if image_code_client.lower() != image_code_server.lower():
            return JsonResponse({'code':400,'errmsg':'图片验证码错误'})

        # 4、生成短信验证码
        sms_code = '%06d'%random.randint(0,999999)
        # 5、保存短信验证码
        redis_conn.setex('sms_%s'%mobile,300,sms_code)
        # 6、发送短信验证码
        CCP().send_template_sms(mobile,[sms_code,5],1)
        # 7、响应结果
        return JsonResponse({'code':0,'errmsg':'ok'})