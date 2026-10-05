# Unprivileged Nginx: runs as non-root and listens on 8080
FROM nginxinc/nginx-unprivileged:1.27-alpine

# API_UPSTREAM is substituted into the config at container start (envsubst templates)
ENV API_UPSTREAM=api:8000
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY index.html app.js style.css /usr/share/nginx/html/

EXPOSE 8080
