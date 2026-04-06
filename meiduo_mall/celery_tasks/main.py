from celery import Celery
import os
# 为celery启动时指定django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meiduo_mall.settings')
# 创建celery对象
celery_app = Celery('celery_tasks')
# celery 配置
celery_app.config_from_object('celery_tasks.config')
# celery 自动注册任务
celery_app.autodiscover_tasks(['celery_tasks.sms'])