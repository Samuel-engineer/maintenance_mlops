# ── Stage 1 : build Vite ────────────────────────────────────────────────────
# Contexte de build : dossier app/  (docker build app/)
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2 : serveur nginx ──────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Supprime la config par défaut et copie les assets compilés
RUN rm /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# Config nginx : proxy /api → conteneur api, SPA fallback sur index.html
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location /api/ {\n\
        proxy_pass http://api:8000/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
    }\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/app.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
