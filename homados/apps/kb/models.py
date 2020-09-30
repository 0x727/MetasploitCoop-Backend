from django.db import models

# Create your models here.


class MsfModuleManual(models.Model):
    fullname = models.CharField(max_length=100, db_index=True, verbose_name='模块名')
    title = models.CharField(max_length=100, verbose_name='模块中文译名')
    intro = models.TextField(default='', verbose_name='模块介绍')
    options = models.TextField(null=True, verbose_name='模块选项翻译')
    created_at = models.DateTimeField(null=True, auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(null=True, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'msf_module_manual'


class TranslationBase(models.Model):
    en_source = models.TextField(verbose_name='英文')
    zh_target = models.TextField(verbose_name='翻译')
    created_at = models.DateTimeField(null=True, auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(null=True, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'translation_base'
