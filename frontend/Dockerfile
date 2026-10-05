# Frontend image only. Vite inlines VITE_* vars into the static bundle at
# BUILD time, not container start. Default is a relative path, not an
# absolute host:port — nginx.conf proxies /api/ to the backend on the same
# origin, so the browser always calls back whatever origin served the page.
# That makes one image work unmodified on any host/port/domain (HTTP or
# HTTPS) without rebuilding. Only override VITE_API_BASE_URL if the backend
# is NOT reachable through this container's own nginx proxy.
FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 5174
