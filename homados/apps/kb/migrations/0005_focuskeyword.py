# Generated by Django 3.1.1 on 2020-09-30 08:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kb', '0004_translationbase'),
    ]

    operations = [
        migrations.CreateModel(
            name='FocusKeyword',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('word', models.CharField(max_length=200, verbose_name='关键词')),
                ('category', models.CharField(db_index=True, max_length=100, verbose_name='分类')),
                ('description', models.TextField(verbose_name='描述')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'db_table': 'focus_keywords',
            },
        ),
    ]