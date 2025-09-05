# Team Task Manager Web Application

A Django-based Team Task Manager that allows teams to create projects, manage tasks, and collaborate effectively.  
The app provides both a **traditional web interface** and a REST API for external clients.  

Features
- Custom User model with email as login
- Projects & tasks management
- Authentication (Register/Login/Logout)
- Permissions (project owners & task assignees)
- PostgreSQL + Redis
- REST API (DRF, JWT, filters, pagination, search)
- Real-time updates with Channels
- Dockerized for easy setup

Tech stack
- Backend: Django 5, Django REST Framework  
- Database: PostgreSQL  
- Auth:JWT (SimpleJWT)  
- Realtime: Django Channels + Redis  
- Containerization:Docker, docker-compose  
- Deployment Ready:Gunicorn + Nginx

How to Run
 
 - Copy `.env.example` to `.env` and fill in secrets
- `.env.example` is tracked; `.env` is ignored

- The app runs with Docker using `docker-compose up --build`
- Containers include: Django, PostgreSQL, Redis


```bash
git clone https://github.com/<your-username>/CoreWebpplication.git
cd CoreWebpplication
