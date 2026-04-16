from django.db import models

# Create your models here.

class Areas(models.Model):
    """地区表"""
    name = models.CharField(max_length=20, verbose_name='名称')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subs',
                               verbose_name='上级行政区划')

    class Meta:
        db_table = 'tb_areas'
        verbose_name = '省市区'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name