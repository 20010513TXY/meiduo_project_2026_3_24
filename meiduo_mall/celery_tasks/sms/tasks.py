from celery_tasks.main import celery_app
from libs.yuntongxun.sms import CCP
import logging
logger = logging.getLogger('django')

@celery_app.task(name='send_sms_code')
def send_sms_code(mobile,sms_code):
    """发送短信的异步任务"""
    try:
        send_ret = CCP().send_template_sms(mobile,[sms_code,5],1)
    except Exception as e:
        logger.error(e)