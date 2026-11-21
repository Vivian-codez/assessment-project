# syntax=docker/dockerfile:1
# Multi-stage production Dockerfile for Verism AI React / TanStack Frontend

# Stage 1: Build and compile frontend static assets
FROM node:24-alpine AS builder

# Set working directory for client compilation
WORKDIR /app

# Copy package manifests for deterministic package installation
COPY package*.json ./

# Install project dependencies with clean npm install
RUN npm ci || npm install

# Copy complete frontend source tree into container
COPY . .

# Set production environment flag for compiler optimizations
ENV NODE_ENV=production

# Compile application assets into production bundle (.output/public)
RUN npm run build


# Stage 2: Serve compiled static assets via lightweight Nginx Alpine container
FROM nginx:alpine AS runner

# Remove default Nginx welcome configuration file
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom Nginx server configuration into conf.d directory
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled production assets from builder stage into Nginx document root
COPY --from=builder /app/.output/public /usr/share/nginx/html

# Ensure proper read permissions for web server process
RUN chmod -R 755 /usr/share/nginx/html

# Expose TCP network port 3000 matching Nginx listen directive
EXPOSE 3000

# Specify container entrypoint command launching Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
