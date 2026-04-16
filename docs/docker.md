# Docker Commands

**Rebuild and restart (no cache):**
```
docker-compose down && docker-compose build --no-cache && docker-compose up -d
```

**View running containers:**
```
docker-compose ps
```

**View logs:**
```
docker-compose logs -f
```
