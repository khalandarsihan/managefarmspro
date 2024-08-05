# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    mariadb-client \
    curl \
    gnupg \
    git \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and Yarn
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g yarn

# Install Frappe Bench
RUN pip install frappe-bench

# Create a non-root user
RUN useradd -m frappe \
    && echo "frappe ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set the working directory
WORKDIR /workspace/development

# Switch to the non-root user
USER frappe

# Initialize a new bench
RUN bench init --skip-redis-config-generation --skip-assets --python "$(which python)" frappe-bench

# Set up MariaDB server settings
RUN sudo mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL character_set_server = 'utf8mb4'" \
    && sudo mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"

# Copy the Frappe app into the container
COPY . /workspace/development/frappe-bench/apps/managefarmspro

# Get the Frappe app
RUN bench get-app managefarmspro /workspace/development/frappe-bench/apps/managefarmspro

# Set up the site
RUN bench new-site --db-root-password root --admin-password admin test_site \
    && bench --site test_site install-app managefarmspro

# Expose port 8000
EXPOSE 8000

# Start Frappe
CMD ["bench", "start"]

