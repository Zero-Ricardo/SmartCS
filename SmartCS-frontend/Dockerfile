# ============ 第一阶段：构建 ============
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:20-alpine AS builder

WORKDIR /app

# 使用 pnpm
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate

# 先复制 package.json
COPY package.json ./

# 安装依赖（使用 pnpm-lock.yaml 如果存在，否则使用 package-lock.json）
RUN if [ -f pnpm-lock.yaml ]; then \
        pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
        pnpm install; \
    else \
        pnpm install; \
    fi

# 复制源代码
COPY . .

# 构建参数
# 生产环境 VITE_API_BASE_URL 为空，使用相对路径
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# 构建
RUN pnpm build

# ============ 第二阶段：运行 ============
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nginx:1.27-alpine

# 删除默认配置和占位文件
RUN rm -rf /etc/nginx/conf.d/default.conf /usr/share/nginx/html/*

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置模板（含 ${INTERNAL_SECRET} 占位符）
COPY nginx.conf /etc/nginx/templates/default.conf.template

# 默认 secret（docker-compose 或 -e 覆盖）
ENV INTERNAL_SECRET=your-internal-secret-key

EXPOSE 80

# 用 envsubst 替换 nginx 模板中的环境变量，然后启动 nginx
CMD ["/bin/sh", "-c", "envsubst '${INTERNAL_SECRET}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
