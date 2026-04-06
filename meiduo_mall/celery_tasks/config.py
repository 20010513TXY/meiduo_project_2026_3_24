# 指定broker和backend
# broker 是任务队列，backend是任务结果存储
broker_url = 'redis://:123456@127.0.0.1:6379/14'
result_backend = 'redis://:123456@127.0.0.1:6379/15'