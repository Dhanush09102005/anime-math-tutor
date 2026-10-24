# ── Build stage ───────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci --frozen-lockfile

COPY . .

# VITE_API_URL is passed as a build arg from docker-compose and embedded
# into the built JS at build time (Vite replaces import.meta.env.VITE_API_URL).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Serve stage ───────────────────────────────────────────────────────────────
# nginx serves the built static files and handles client-side routing by
# falling back to index.html for any path that isn't a real file.
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx config so React Router's client-side routes (e.g. /dashboard,
# /history/:id) don't 404 on hard refresh.
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
