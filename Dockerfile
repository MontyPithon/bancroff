FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    make \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories and set permissions first
RUN mkdir -p /app/instance /app/uploads /app/static/uploads && \
    chmod -R 777 /app/instance /app/uploads /app/static/uploads

# Copy only requirements file first for better caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy application code
COPY . /app/

# Set permissions for all application files
RUN chmod -R 777 /app

# Expose the port
EXPOSE 50010

# Run the application
CMD ["python", "app.py"] 