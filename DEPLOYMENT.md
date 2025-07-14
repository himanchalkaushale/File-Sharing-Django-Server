# Deployment Guide - FileShare

This guide covers deploying the FileShare application to various hosting platforms and production environments.

## 🚀 Quick Deployment Options

### 1. Railway (Recommended for Beginners)
- Free tier available
- Automatic deployments from GitHub
- Built-in PostgreSQL database

### 2. Heroku
- Easy deployment process
- Good free tier (limited)
- Automatic scaling

### 3. DigitalOcean App Platform
- Simple deployment
- Good performance
- Reasonable pricing

### 4. AWS/GCP/Azure
- Full control
- Scalable
- More complex setup

## 📋 Pre-Deployment Checklist

- [ ] Set `DEBUG = False` in production
- [ ] Generate new `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up production database
- [ ] Configure static file serving
- [ ] Set up environment variables
- [ ] Test locally with production settings

## 🔧 Production Configuration

### 1. Environment Variables
Create a `.env` file for production:
```env
SECRET_KEY=your-super-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=your-database-url
```

### 2. Update Settings
Modify `settings.py` for production:
```python
import os
from decouple import config

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Database (for PostgreSQL)
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
}

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### 3. Install Additional Dependencies
Add to `requirements.txt`:
```
dj-database-url==2.1.0
psycopg2-binary==2.9.9
```

## 🚀 Railway Deployment

### 1. Prepare Repository
```bash
# Add Procfile
echo "web: gunicorn file_sharing_project.wsgi:application" > Procfile

# Add runtime.txt
echo "python-3.11.0" > runtime.txt
```

### 2. Deploy to Railway
1. Go to [Railway.app](https://railway.app)
2. Connect your GitHub repository
3. Add PostgreSQL database
4. Set environment variables
5. Deploy

### 3. Environment Variables (Railway)
```
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-app.railway.app
DATABASE_URL=postgresql://...
```

## 🚀 Heroku Deployment

### 1. Install Heroku CLI
```bash
# Download from https://devcenter.heroku.com/articles/heroku-cli
```

### 2. Create Heroku App
```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:mini
```

### 3. Configure Environment
```bash
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS=your-app.herokuapp.com
```

### 4. Deploy
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
heroku run python manage.py migrate
```

## 🚀 DigitalOcean App Platform

### 1. Create App
1. Go to DigitalOcean App Platform
2. Connect your GitHub repository
3. Choose Python environment
4. Configure build settings

### 2. Build Configuration
```yaml
# .do/app.yaml
name: fileshare
services:
- name: web
  source_dir: /
  github:
    repo: your-username/your-repo
    branch: main
  run_command: gunicorn file_sharing_project.wsgi:application
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: SECRET_KEY
    value: your-secret-key
  - key: DEBUG
    value: "False"
  - key: ALLOWED_HOSTS
    value: your-app.ondigitalocean.app
```

## 🚀 AWS EC2 Deployment

### 1. Launch EC2 Instance
- Choose Ubuntu 20.04 LTS
- Configure security groups (port 80, 443, 22)
- Generate key pair

### 2. Connect and Setup
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3-pip python3-venv nginx -y
```

### 3. Deploy Application
```bash
# Clone repository
git clone your-repo-url
cd your-repo

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp env_example.txt .env
# Edit .env with production settings

# Setup database
python manage.py migrate
python manage.py collectstatic

# Create systemd service
sudo nano /etc/systemd/system/fileshare.service
```

### 4. Systemd Service
```ini
[Unit]
Description=FileShare Django Application
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/your-repo
Environment="PATH=/home/ubuntu/your-repo/venv/bin"
ExecStart=/home/ubuntu/your-repo/venv/bin/gunicorn file_sharing_project.wsgi:application --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5. Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/fileshare
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/ubuntu/your-repo;
    }

    location /media/ {
        root /home/ubuntu/your-repo;
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### 6. Enable Services
```bash
sudo systemctl start fileshare
sudo systemctl enable fileshare
sudo ln -s /etc/nginx/sites-available/fileshare /etc/nginx/sites-enabled
sudo systemctl restart nginx
```

## 🚀 Docker Deployment

### 1. Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create media directory
RUN mkdir -p media/uploads

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run application
CMD ["gunicorn", "file_sharing_project.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### 2. Create docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=your-secret-key
      - DEBUG=False
      - ALLOWED_HOSTS=localhost,127.0.0.1
    volumes:
      - ./media:/app/media
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=fileshare
      - POSTGRES_USER=fileshare
      - POSTGRES_PASSWORD=your-password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 3. Deploy with Docker
```bash
docker-compose up -d
```

## 🔒 SSL/HTTPS Setup

### Let's Encrypt (Free SSL)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoring and Logging

### 1. Application Logs
```bash
# View logs
sudo journalctl -u fileshare -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 2. Performance Monitoring
Consider using:
- New Relic
- DataDog
- AWS CloudWatch
- Google Analytics

## 🔄 Backup Strategy

### 1. Database Backup
```bash
# PostgreSQL
pg_dump your_database > backup.sql

# SQLite
cp db.sqlite3 backup.sqlite3
```

### 2. File Backup
```bash
# Backup uploaded files
tar -czf media_backup.tar.gz media/
```

### 3. Automated Backups
```bash
# Create backup script
nano backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Database backup
pg_dump $DATABASE_URL > $BACKUP_DIR/db_$DATE.sql

# File backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

## 🚨 Troubleshooting

### Common Issues

1. **Static files not loading**
   - Run `python manage.py collectstatic`
   - Check STATIC_ROOT configuration

2. **Database connection errors**
   - Verify DATABASE_URL
   - Check database permissions

3. **File upload errors**
   - Check file permissions on media directory
   - Verify file size limits

4. **500 Internal Server Error**
   - Check application logs
   - Verify DEBUG=False in production

### Performance Optimization

1. **Enable caching**
2. **Use CDN for static files**
3. **Optimize database queries**
4. **Use background tasks for file processing**

## 📞 Support

For deployment issues:
1. Check the logs
2. Verify configuration
3. Test locally with production settings
4. Consult platform-specific documentation

---

**Happy Deploying! 🚀** 