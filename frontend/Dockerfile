# Unprivileged Nginx: runs as non-root and listens on 8080
FROM nginxinc/nginx-unprivileged:stable-alpine

# Pull in the latest Alpine security patches (e.g. OpenSSL), then drop back to the non-root user
USER root
RUN apk upgrade --no-cache
USER 101

# API_UPSTREAM is substituted into the config at container start (envsubst templates)
ENV API_UPSTREAM=api:8000
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY index.html app.js style.css /usr/share/nginx/html/

EXPOSE 8080
