from django.shortcuts import render
from django.views import View
from libs.captcha.captcha import captcha
from django.http import HttpResponse
from django_redis import get_redis_connection

# Create your views here.
class ImageCodeView(View):
    """图片验证码"""
    def get(self,request,uuid):
        text,image = captcha.generate_captcha()
        get_conn = get_redis_connection('code')
        get_conn.setex('img_%s'%uuid,300,text)
        return HttpResponse(image,content_type='image/jpeg')
