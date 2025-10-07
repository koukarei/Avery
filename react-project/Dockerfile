FROM node:22-slim AS builder
WORKDIR /app

# Install dependencies using package-lock from the subproject
COPY avery_analytics_vite/package*.json ./
COPY avery_analytics_vite/package-lock.json ./
RUN npm ci

# Copy the subproject source and build the app
COPY avery_analytics_vite/ ./
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
RUN chmod -R 755 /usr/share/nginx/html