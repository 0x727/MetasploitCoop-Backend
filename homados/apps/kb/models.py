from django.db import models

# Create your models here.


class MsfModuleManual(models.Model):
    fullname = models.CharField(max_length=100, db_index=True, verbose_name='模块名')
    title = models.CharField(max_length=100, verbose_name='模块中文译名')
    intro = models.TextField(default='', verbose_name='模块介绍')
    options = models.TextField(null=True, verbose_name='模块选项翻译')

    class Meta:
        db_table = 'msf_module_manual'
