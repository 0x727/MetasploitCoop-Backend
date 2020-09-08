from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField

# Create your models here.


class Modules(models.Model):
    """msf 模块表"""
    name = models.CharField(max_length=250, blank=True, verbose_name='模块名')
    fullname = models.CharField(max_length=100, db_index=True, verbose_name='模块完整名')
    aliases = ArrayField(models.CharField(max_length=50, blank=True, verbose_name='别名'))
    disclosure_date = models.CharField(max_length=30, null=True, verbose_name='披露时间')
    rank = models.IntegerField(verbose_name='评分', null=True)
    type = models.CharField(max_length=10, db_index=True, blank=True, verbose_name='类型')
    description = models.TextField(blank=True, verbose_name='描述')
    author = ArrayField(models.CharField(max_length=100, blank=True), verbose_name='作者')
    references = ArrayField(models.CharField(max_length=100, blank=True), verbose_name='参考资料')
    platform = models.CharField(max_length=250, blank=True, verbose_name='平台')
    arch = models.CharField(max_length=250, blank=True, verbose_name='架构')
    rport = models.IntegerField(null=True, verbose_name='远端端口')
    mod_time = models.CharField(max_length=30, null=True, verbose_name='更新时间')
    ref_name = models.CharField(max_length=100, db_index=True, verbose_name='模块标识')
    path = models.CharField(max_length=100, verbose_name='模块路径')
    is_install_path = models.BooleanField(default=False)
    targets = ArrayField(models.CharField(max_length=100, blank=True), null=True, verbose_name='目标平台')
    info_html = models.TextField(null=True, verbose_name='详细介绍')
    compatible_payloads = ArrayField(models.CharField(max_length=100, blank=True), null=True, verbose_name='exp兼容payload')
    options = JSONField(null=True, verbose_name='模块选项')
