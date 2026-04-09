from django.http import JsonResponse

class LoginRequiredJSONMixin(object):
    """
    JSON格式数据，登录验证
    """
    def handle_no_permission(self):
        return JsonResponse({'code':400,'errmsg':'用户未登录'})