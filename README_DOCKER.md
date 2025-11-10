## Local WordPress test environment (Docker)

This repository contains a WordPress theme at `rmk-theme/`. The docker-compose setup below lets you run a disposable local WordPress site for development and testing.

Files added:
- `docker-compose.yml` - WordPress, MySQL and phpMyAdmin services
- `.env.example` - example environment variables (copy to `.env` and edit)
- `.dockerignore` - avoid big files in Docker context

Quick start (PowerShell):

1. Copy the example env and edit if you want custom passwords/ports:

```powershell
cp .env.example .env
# then edit .env in your editor
```

2. Start the stack in the background:

```powershell
docker compose up -d
```

3. Open the site in your browser:

- WordPress front-end: http://localhost:8000
- phpMyAdmin: http://localhost:8080 (use root user and DB root password from `.env`)

Notes and tips:
- The `rmk-theme` folder is mounted into the container at `wp-content/themes/rmk-theme` so you can edit theme files locally and see the changes immediately.
- Uploads are persisted in a named Docker volume `uploads` so media survives restarts.
- To stop and remove containers (preserves volumes):

```powershell
docker compose down
```

- To remove containers and volumes (reset DB and uploads):

```powershell
docker compose down -v
```

- If Docker Desktop or your environment restricts file sharing on Windows, ensure the project folder is allowed in Docker Desktop settings so volume mounts work.

Next steps you might want:
- Add a small script to provision default options or to import SQL dumps into the DB.
- Add `docker-compose.override.yml` for alternate dev settings.
