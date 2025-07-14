# File Sharing Web

A Django-based web application for easy file sharing on local networks or the internet. Designed for simplicity and large file support, with an admin panel for file management.

## Features
- Upload and share files of any type (up to 100GB per file by default)
- Public access: No login or signup required for users
- Short link generation for easy sharing
- File integrity verification (MD5, SHA256)
- Admin panel for managing files and short links
- Mobile-friendly interface
- QR code for quick access on phones

## Requirements
- Python 3.8+
- Django 5.x
- [python-decouple](https://pypi.org/project/python-decouple/)
- (Optional) [django-storages](https://django-storages.readthedocs.io/en/latest/) for cloud storage

## Setup Instructions

1. **Clone the repository:**
   ```sh
   git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
   cd File-Sharing-Web
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   - Copy `env_example.txt` to `.env` and set your `SECRET_KEY` and other settings as needed.

5. **Apply migrations:**
   ```sh
   python manage.py migrate
   ```

6. **Create a superuser for the admin panel:**
   ```sh
   python manage.py createsuperuser
   ```

7. **Run the development server:**
   ```sh
   python manage.py runserver 0.0.0.0:8000
   ```
   - Access the site at `http://<your-ip>:8000/` from any device on the same network.
   - Admin panel: `http://<your-ip>:8000/admin/`

## File Uploads & Storage
- Uploaded files are stored in the `media/` directory by default.
- For production, configure cloud storage (e.g., Amazon S3) for persistent and scalable file storage.

## Deployment
- For public access, deploy to a cloud server (e.g., DigitalOcean, AWS EC2) or use a platform like Heroku (with external storage).
- Update `ALLOWED_HOSTS` in `settings.py` for your domain or server IP.
- Use a production-ready web server (e.g., Gunicorn, Nginx).

## Security Notes
- The public site has no authentication; anyone with the link can upload/download files.
- The admin panel is protected and requires a superuser login.
- Keep your `SECRET_KEY` and credentials safe (do not commit them to GitHub).

## Admin Panel
- Access at `/admin/` with your superuser account.
- Manage files, short links, and view file integrity status.

## License
MIT License

---

**Contributions and feedback are welcome!** 