import os
import sys
import subprocess
import psycopg2
import htpasswd
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def exec_cmd(cmd, cwd=None):
    proc = subprocess.call(cmd, shell=True, cwd=cwd)
    if proc:
        raise Exception(f'[!] {cmd} failed')
    print(f'[o] {cmd} succ')


path = "/root/.msf4/"
_pg_user = os.getenv('HOMADOS_PG_USER') or 'postgres'
_pg_pass = os.getenv('HOMADOS_PG_PASS') or 'homados@123'
_pg_host = os.getenv('HOMADOS_PG_SERVER') or '127.0.0.1'
_pg_port = os.getenv('HOMADOS_PG_PORT') or '5432'

# 判断是否存在.msf4文件夹，存在则代表已初始化
if not os.path.exists(path):
    os.makedirs(path)
else:
    sys.exit(0)

# 创建数据库配置文件
with open(f'{path}/database.yml', 'w') as f:
    f.write(f'''
development: &pgsql
  adapter: postgresql
  database: msf
  username: {_pg_user}
  password: {_pg_pass}
  host: {_pg_host}
  port: {_pg_port}
  pool: 200

production: &production
  <<: *pgsql

test:
  <<: *pgsql
  database: msftest
  username: {_pg_user}
  password: {_pg_pass}
''')

# 创建并迁移msf数据库
exec_cmd('bundle exec rake db:create', cwd='/root/metasploit-framework')
exec_cmd('bundle exec rake db:migrate', cwd='/root/metasploit-framework')

# 创建homados数据库
conn = psycopg2.connect(dbname='postgres', user=_pg_user, password=_pg_pass, host=_pg_host, port=_pg_port)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
try:
    cur.execute("CREATE DATABASE homados")
except psycopg2.errors.DuplicateDatabase as e:
    print('database "homados" already exists')

# 迁移homaods数据库
exec_cmd('python3 manage.py migrate kb --database=kbase', cwd='/root/homados')
exec_cmd('python3 manage.py migrate', cwd='/root/homados')
exec_cmd('python3 manage.py createcachetable', cwd='/root/homados')

# 修改 nginx htpasswd
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')
if username and password:
    with htpasswd.Basic('/etc/htpasswd') as userdb:
        try:
            userdb.add(username, password)
        except htpasswd.basic.UserExists as e:
            userdb.change_password(username, password)
