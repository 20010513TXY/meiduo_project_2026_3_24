from celery_tasks.main import celery_app
from django.core.mail import send_mail
from libs.yuntongxun.sms import CCP
import logging
logger = logging.getLogger('django')
from meiduo_mall import settings

@celery_app.task(name='send_verify_email')
def send_verify_email(subject, message, from_email, recipient_list,html_message):
    """发送邮件的异步任务"""
    try:
        send_mail(subject, message, from_email, recipient_list, html_message=html_message)
    except Exception as e:
        logger.error(e)