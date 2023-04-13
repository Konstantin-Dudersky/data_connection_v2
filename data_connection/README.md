## Тестирование

Перед запуском тестов запустить docker:

```bash
do -i {docker start redis-stack} ; docker run -d --rm --name redis-stack -p 6379:6379 -p 8010:8001 redis/redis-stack:latest
```
