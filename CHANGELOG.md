## 20201018

1. 文字聊天功能
2. 支持模块执行选项的提示说明
3. 支持会话路由操作支持
4. 支持查询主机历史会话的命令和模块执行记录
5. 截图依据ip存放到不同的目录
6. 支持查阅会话历史记录
7. 会话添加回连（公网）ip端口展示
8. 支持开放或关闭注册功能，增加安全性
9. 支持可配置右键菜单
10. 文件管理支持无限滚动与搜索，防止渲染过多卡死
11. 战利品和凭证列表无限滚动
12. 修正：主机用户名的显示
13. 修正：一些信息列表支持手动拖拽宽度
14. 主机存活状态自动更新
15. 增加 https://github.com/0x727/MetasploitModules_0x727 模块
    1. mssql_powershell: 通过正确的SQL Server口令信息，可启用xp_cmdshell，并获取目标系统session。
    2. clone_user: 创建登录账户，添加该账户到管理员与远程桌面组，并克隆administrator，从而替代clone.exe( 支持尝试提权，默认随机8位密码，用户不能设置Guest，应用RID劫持技术)
    3. redis/unauthorized: 批量扫描Redis未授权漏洞，若存在，探测/root/.ssh/与/var/spool/cron/目录权限，可写入id_rsa.pub到目标服务器（id_rsa.pub应设置绝对路径），或提示Cron反弹命令。
    4. ...更多查看（https://github.com/0x727/MetasploitModules_0x727）
16. 增加内存执行exe的模块(post/windows/manage/execute_pe)（需要exe存在.reloc节，比如golang编译的exe，并且payload与目标主机架构需要相同）
17. 新增模块或选项后自动翻译
18. 重启容器后自动恢复之前的监听
19. 支持客户端使用（目前只支持win，后续将添加其他版本客户端）
