from itsdangerous import URLSafeTimedSerializer as Serializer
from meiduo_mall import settings
from apps.users.models import User
def generate_email_verify_url(user_id):
    # 创建实例
    # 加密数据
    # 返回数据
    serializer = Serializer(settings.SECRET_KEY)
    data = serializer.dumps({'user_id': user_id})
    return data

def check_email_verify_url(token):
    """
    验证邮箱验证URL
    :param token: 邮箱验证URL
    :return: user
    """
    serializer = Serializer(settings.SECRET_KEY)
    try:
        data = serializer.loads(token)
    except:
        return None
    else:
        user_id = data.get('user_id')
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
        else:
            return user