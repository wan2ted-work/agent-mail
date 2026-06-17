# ─── Build stage ───────────────────────────────────────────────────────────
FROM node:18-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# VITE_ vars are baked in at build time.
ARG VITE_API_URL=http://localhost:8080
ARG VITE_EMAIL_DOMAIN=example.com
ARG VITE_MAIL_HOST=
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_EMAIL_DOMAIN=$VITE_EMAIL_DOMAIN
ENV VITE_MAIL_HOST=$VITE_MAIL_HOST

RUN npm run build

# ─── Runtime stage ─────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
