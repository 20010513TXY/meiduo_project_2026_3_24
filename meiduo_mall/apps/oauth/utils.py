from itsdangerous import URLSafeTimedSerializer as Serializer
from meiduo_mall import settings
def generate_access_token(openid):
    """
    生成access_token
    :param user:
    :return:
    """
    serializer = Serializer(settings.SECRET_KEY,expires_in=300)
    token = serializer.dumps({'openid':openid})
    return token.decode()

def check_access_token(access_token):
    """
    检验access_token
    :param token:
    :return:
    """
    serializer = Serializer(settings.SECRET_KEY,expires_in=300)
    try:
        data = serializer.loads(access_token)
    except:
        return None
    else:
        return data.get('openid')