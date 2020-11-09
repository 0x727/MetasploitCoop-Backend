from django.db import models

# Create your models here.


class MsfModuleManual(models.Model):
    """模块说明书表"""
    fullname = models.CharField(max_length=100, db_index=True, verbose_name='模块名')
    title = models.CharField(max_length=100, verbose_name='模块中文译名')
    intro = models.TextField(default='', verbose_name='模块介绍')
    options = models.TextField(null=True, verbose_name='模块选项翻译')
    created_at = models.DateTimeField(null=True, auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(null=True, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'msf_module_manual'


class TranslationBase(models.Model):
    """翻译句子基础表"""
    en_source = models.TextField(verbose_name='英文')
    zh_target = models.TextField(verbose_name='翻译')
    created_at = models.DateTimeField(null=True, auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(null=True, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'translation_base'


class FocusKeyword(models.Model):
    """关键词表"""
    word = models.CharField(max_length=200, verbose_name='关键词')
    category = models.CharField(max_length=100, db_index=True, verbose_name='分类')
    description = models.TextField(verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'focus_keywords'


class ContextMenu(models.Model):
    """公共右键菜单表"""
    text = models.CharField(max_length=50, verbose_name='菜单文本')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    description = models.TextField(null=True, blank=True, verbose_name='描述')
    type = models.CharField(max_length=50, verbose_name='右键菜单类型')
    addition = models.TextField(null=True, verbose_name='额外选项')
    is_autorun = models.BooleanField(default=False, verbose_name='是否直接自动执行')
    pid = models.ForeignKey(default=0, to='self', on_delete=models.CASCADE, db_constraint=False)


class ResourceScript(models.Model):
    """资源脚本"""
    title = models.CharField(default='', max_length=100, verbose_name='脚本标题')
    description = models.TextField(default='', verbose_name='脚本介绍')
    filename = models.CharField(max_length=100, unique=True, verbose_name='脚本文件名')
    content = models.TextField(verbose_name='脚本内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'resource_scripts'
