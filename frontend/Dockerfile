# Build from the repository root (the build needs the root package files and /shared):
#   docker build -f frontend/Dockerfile .
FROM node:22-alpine AS build
WORKDIR /repo

# Packages first, so this layer is cached until a package file changes.
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/
RUN npm ci --ignore-scripts

COPY frontend ./frontend
COPY shared ./shared
RUN npm run build -w frontend

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/frontend/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
