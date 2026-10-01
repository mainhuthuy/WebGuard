# Frontend Dockerfile
FROM node:22-alpine AS build

WORKDIR /app

# Dependencies are locked with npm (package-lock.json)
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production serve with nginx
FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# Development stage
FROM node:22-alpine AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
