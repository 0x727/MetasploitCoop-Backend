FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive

RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list &&\
    apt update &&\
    apt install -y python3 python3-pip nginx curl libssl-dev libreadline-dev tzdata &&\
    pip3 install supervisor

ENV TZ Asia/Shanghai

COPY ./rbenv /root/.rbenv

# 安装 ruby
RUN /root/.rbenv/bin/rbenv install 2.6.6 && \
    /root/.rbenv/versions/2.6.6/bin/gem sources --add https://mirrors.tuna.tsinghua.edu.cn/rubygems/ --remove https://rubygems.org/ && \
    /root/.rbenv/versions/2.6.6/bin/gem install bundler && \
    /root/.rbenv/versions/2.6.6/bin/bundle config mirror.https://rubygems.org https://mirrors.tuna.tsinghua.edu.cn/rubygems && \
    mkdir /root/deps

# 安装msf依赖
COPY ./metasploit-framework/Gemfile* ./metasploit-framework/metasploit-framework.gemspec ./metasploit-framework/Rakefile /root/metasploit-framework/
COPY ./metasploit-framework/lib/metasploit/framework/version.rb /root/metasploit-framework/lib/metasploit/framework/version.rb
COPY ./metasploit-framework/lib/metasploit/framework/rails_version_constraint.rb /root/metasploit-framework/lib/metasploit/framework/rails_version_constraint.rb
COPY ./metasploit-framework/lib/msf/util/helper.rb /root/metasploit-framework/lib/msf/util/helper.rb

RUN apt install -y git autoconf build-essential libpcap-dev libpq-dev zlib1g-dev libsqlite3-dev &&\
    cd /root/metasploit-framework/ && \
    /root/.rbenv/versions/2.6.6/bin/bundle install

# 安装PEzor
COPY ./install_scripts/pezor.sh /root/deps/
RUN bash /root/deps/pezor.sh

# 安装homados依赖
COPY ./requirements.txt /root/deps/
RUN cd /root/deps && \
    pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple

COPY ./metasploit-framework /root/metasploit-framework
COPY ./homados /root/homados
COPY ./front /srv/http/front
COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./initdb.py /root
COPY ./supervisord.conf /etc/supervisor/supervisord.conf
COPY ./htpasswd /etc/htpasswd
COPY ./cert /root/cert
COPY ./dep_tools/donut /root/donut
COPY ./dep_tools/sgn /root/sgn

ENV PATH "$PATH:/root/.rbenv/versions/2.6.6/bin:/root/donut:/root/sgn:/root/PEzor:/root/PEzor/deps/wclang/_prefix_PEzor_/bin/"
ENV MSF_WS_JSON_RPC_API_TOKEN "homados"
