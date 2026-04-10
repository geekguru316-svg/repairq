FROM python:3.11

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose Railway port
EXPOSE 8080

# Start app + run migrations
CMD ["sh", "-c", "python manage.py migrate && gunicorn repairq.wsgi:application --bind 0.0.0.0:8080"]
