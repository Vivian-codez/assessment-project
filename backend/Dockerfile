# syntax=docker/dockerfile:1
# Multi-stage production Dockerfile for Verism AI FastAPI Backend Service

# Stage 1: Build compilation environment and Python virtualenv dependencies
FROM python:3.11-slim AS builder

# Set environment variable to disable writing bytecode .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Set environment variable to enable unbuffered console output for real-time logging
ENV PYTHONUNBUFFERED=1

# Install Debian build prerequisites and PostgreSQL client development libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Install C compiler for compiling native Python packages like psycopg2 and bcrypt
    build-essential \
    # Install PostgreSQL header files and library development package
    libpq-dev \
    # Install curl utility for network downloads and connectivity diagnostics
    curl \
    # Clean up apt package cache to minimize intermediate layer footprint
    && rm -rf /var/lib/apt/lists/*

# Set working directory for the builder stage
WORKDIR /install

# Copy requirements specification file from host repository
COPY requirements.txt .

# Upgrade pip and install all Python requirements into local prefix folder
RUN pip install --no-cache-dir --upgrade pip && \
    # Install dependencies into /install prefix for clean multi-stage transfer
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Lean runtime environment with non-root security isolation
FROM python:3.11-slim AS runner

# Set environment variable to disable writing bytecode files
ENV PYTHONDONTWRITEBYTECODE=1
# Set environment variable for unbuffered runtime logging
ENV PYTHONUNBUFFERED=1
# Set Python path to include application root directory
ENV PYTHONPATH=/app

# Install minimal runtime shared libraries required by PostgreSQL and PDF utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Install PostgreSQL client runtime library for psycopg2
    libpq5 \
    # Install curl utility for container health checks
    curl \
    # Clean up apt package cache to keep final image slim
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group with UID/GID 10001
RUN groupadd -g 10001 verism && \
    # Create system user verism associated with verism group
    useradd -u 10001 -g verism -s /bin/sh -m verism

# Set working directory inside application container
WORKDIR /app

# Copy installed Python packages from builder stage into system Python path
COPY --from=builder /install /usr/local

# Copy backend source code files into the application directory
COPY . /app

# Create persistent storage directories for uploads and temporary processing
RUN mkdir -p /app/uploads /app/uploads/temp && \
    # Assign ownership of application directory to non-root verism user
    chown -R verism:verism /app

# Switch runtime execution context to non-root verism user
USER verism

# Expose network TCP port 8000 for FastAPI ASGI web server
EXPOSE 8000

# Specify default container startup command running Uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
