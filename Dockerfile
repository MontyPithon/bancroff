FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements file first for better caching
COPY requirements.txt /app/

# Create a pip-compatible requirements file
RUN echo "alembic==1.14.1" > /app/requirements.pip && \
    echo "blinker==1.9.0" >> /app/requirements.pip && \
    echo "click==8.1.7" >> /app/requirements.pip && \
    echo "cryptography==43.0.3" >> /app/requirements.pip && \
    echo "dnspython==2.4.2" >> /app/requirements.pip && \
    echo "email-validator==1.2.1" >> /app/requirements.pip && \
    echo "faker==30.8.1" >> /app/requirements.pip && \
    echo "flask==3.1.0" >> /app/requirements.pip && \
    echo "flask-migrate==4.1.0" >> /app/requirements.pip && \
    echo "flask-sqlalchemy==3.1.1" >> /app/requirements.pip && \
    echo "flask-wtf==1.2.1" >> /app/requirements.pip && \
    echo "itsdangerous==2.2.0" >> /app/requirements.pip && \
    echo "jinja2==3.1.5" >> /app/requirements.pip && \
    echo "mako==1.3.9" >> /app/requirements.pip && \
    echo "markupsafe==3.0.2" >> /app/requirements.pip && \
    echo "msal==1.25.0" >> /app/requirements.pip && \
    echo "pycparser==2.21" >> /app/requirements.pip && \
    echo "pyjwt==2.10.1" >> /app/requirements.pip && \
    echo "python-dateutil==2.9.0" >> /app/requirements.pip && \
    echo "python-dotenv==1.0.0" >> /app/requirements.pip && \
    echo "requests==2.32.3" >> /app/requirements.pip && \
    echo "six==1.16.0" >> /app/requirements.pip && \
    echo "sqlalchemy==2.0.37" >> /app/requirements.pip && \
    echo "typing-extensions==4.12.2" >> /app/requirements.pip && \
    echo "urllib3==2.3.0" >> /app/requirements.pip && \
    echo "werkzeug==3.1.3" >> /app/requirements.pip && \
    echo "wtforms==2.3.3" >> /app/requirements.pip

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.pip

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/instance /app/uploads

# Add a non-root user 
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Update app.py to bind to 0.0.0.0 for Docker
RUN sed -i 's/app.run(debug=config.DEBUG, port=config.SERVER_PORT)/app.run(debug=config.DEBUG, host="0.0.0.0", port=config.SERVER_PORT)/g' /app/app.py

# Expose the port
EXPOSE 50010

# Run the application
CMD ["python", "app.py"] 