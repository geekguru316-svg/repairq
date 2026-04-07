FROM python:3.11

# Set unbuffered output for cleaner Docker logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements and install first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose the default port
EXPOSE 8000

# Shell wrapper ensures '&&' is handled correctly, running migrations before start
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]