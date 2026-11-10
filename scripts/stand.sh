#!/usr/bin/env bash
# Демо-стенд (GitHub Codespaces немесе Linux). 11-ЗЖ.
#   bash scripts/stand.sh setup   — бір рет: орнату, дерекқор, тестілік деректер, иесінің аккаунты
#   bash scripts/stand.sh start   — стендті іске қосу (порт 8000)
#   bash scripts/stand.sh stop    — тоқтату
#   bash scripts/stand.sh status  — жауап бере ме
#   bash scripts/stand.sh seed    — тестілік деректерді қайта жасау (seed=42)
#   bash scripts/stand.sh test    — модульдік және интеграциялық тесттер
#   bash scripts/stand.sh e2e     — Playwright сквозной тесттері
#   bash scripts/stand.sh load    — k6 жүктемелік сынағы (3 минут)
#   bash scripts/stand.sh kuma    — Uptime Kuma мониторингі (порт 3001)
set -e
cd "$(dirname "$0")/.."
export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,.app.github.dev"
export DJANGO_CSRF_TRUSTED_ORIGINS="https://*.app.github.dev"
case "$1" in
  setup)
    pip install -q -r requirements.txt -r requirements-dev.txt pytest playwright
    python -m playwright install --with-deps chromium
    (cd src && python manage.py migrate && python manage.py demo_derekter --seed 42)
    echo "Иесінің аккаунтын жасаймыз (құпиясөзді өзіңіз ойлап табыңыз, ол экранда көрінбейді):"
    (cd src && python manage.py createsuperuser --username iesi --email iesi@example.com)
    ;;
  start)
    nohup python src/manage.py runserver 0.0.0.0:8000 > stand.log 2>&1 &
    sleep 3; echo "Стенд іске қосылды: Ports қойындысындағы 8000 портын ашыңыз"
    ;;
  stop)   pkill -f "manage.py runserver" && echo "Стенд тоқтады" || echo "Стенд іске қосылмаған" ;;
  status) curl -s -o /dev/null -w "Жауап коды: %{http_code}, уақыты: %{time_total} с\n" http://localhost:8000/ || echo "Стенд жауап бермейді" ;;
  seed)   (cd src && python manage.py demo_derekter --seed 42) ;;
  test)   (cd src && python manage.py test booking) ;;
  e2e)    pytest tests/e2e -q ;;
  load)   docker run --rm -i --network host -v "$PWD/tests/load:/s" grafana/k6:1.3.0 run /s/zhazylu.js ;;
  kuma)   docker run -d --restart=always --network host -v uptime-kuma:/app/data --name uptime-kuma louislam/uptime-kuma:1
          echo "Uptime Kuma іске қосылды: Ports қойындысында 3001 портын ашыңыз" ;;
  *)      sed -n '2,12p' "$0" ;;
esac
