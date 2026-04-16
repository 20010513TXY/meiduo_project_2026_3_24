from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views import View
from apps.areas.models import Areas
from django.core.cache import cache
import logging

class AreasView(View):
    """省市区数据"""
    def get(self, request):
        province_list = cache.get('province_list')
        if province_list is None:
            try :
                # 获取所有省级数据
                province_model_list = Areas.objects.filter(parent=None)
                province_list = []
                for province_model in province_model_list:
                    province_list.append({'id': province_model.id, 'name': province_model.name})
                cache.set('province_list', province_list, 3600 * 24)
            except Exception as e:
                logging.error(e)
                return JsonResponse({'code':400,'errmsg':'省份数据错误'})
        return JsonResponse({'code':0,'errmsg':'OK','province_list':province_list})

class SubAreasView(View):
    """市或区数据"""
    def get(self, request, pk):
        sub_data = cache.get('sub_data_%s' % pk)
        if sub_data is None:
            try :
                # pk 是 从url中获取的省份 id
                province_model = Areas.objects.get(id=pk)  # 查询主键为pk的省份数据
                sub_model_list = province_model.subs.all() # 通过反向关系获取该省份下的所有子区域（市/区）
                sub_list = [{'id': sub.id, 'name': sub.name} for sub in sub_model_list]
                sub_data = {
                    'id': province_model.id,
                    'name': province_model.name,
                    'subs': sub_list
                }
                cache.set('sub_data_%s' % pk, sub_data, 3600 * 24)
            except Exception as e:
                logging.error(e)
                return JsonResponse({'code':400,'errmsg':'城市或区数据错误'})

        return JsonResponse({'code':0,'errmsg':'OK','sub_data':sub_data})