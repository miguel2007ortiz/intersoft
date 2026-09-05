# =====================================================================
#  InterSoft - Frontend (Angular 22).
#  Multi-stage: build con Node 22 -> serve estatico con nginx alpine.
# =====================================================================

# --- Etapa 1: compilacion (Node 22) ---------------------------------
FROM node:22-alpine AS build

WORKDIR /app

# URL de la API embebida en el build. Por defecto usamos una ruta relativa
# (/api) que el reverse proxy de nginx redirige al backend del compose.
# En un despliegue externo se puede sobreescribir, p.ej. --build-arg API_URL=https://api.intersoft.co/api
ARG API_URL=/api
ENV API_URL=$API_URL

# Separar la instalacion de dependencias (mejor cache de capas).
COPY package.json package-lock.json ./
RUN npm ci

# Codigo fuente y build de produccion.
COPY . .

# Inyectar la URL de la API en el entorno de produccion (Angular compila
# environment.ts en tiempo de build).
RUN sed -i "s#apiUrl: '.*'#apiUrl: '$API_URL'#" src/environments/environment.ts
RUN npm run build

# --- Etapa 2: servidor web (nginx) ----------------------------------
FROM nginx:alpine

# Configuracion SPA: rutas de Angular redirigen a index.html.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar los estaticos compilados.
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
