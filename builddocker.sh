# 构建前端
git clone ssh://git@git.ah-strategy.online:2222/Kali-Team/HomadosFront.git homados_front
cd homados_front && npm install --registry=https://registry.npm.taobao.org && npm run build:prod && mv dist ../front && cd ..

# 克隆rbenv
git clone --depth=1 https://github.com/rbenv/rbenv.git rbenv && rm -rf rbenv/.git &&\
git clone --depth=1 https://github.com/rbenv/ruby-build.git rbenv/plugins/ruby-build && rm -rf rbenv/plugins/ruby-build/.git &&\
git clone --depth=1 https://github.com/andorchen/rbenv-china-mirror.git rbenv/plugins/rbenv-china-mirror && rm -rf rbenv/plugins/rbenv-china-mirror/.git &&\
mkdir rbenv/cache &&\
wget -P rbenv/cache/ https://cache.ruby-china.com/pub/ruby/2.6/ruby-2.6.6.tar.bz2