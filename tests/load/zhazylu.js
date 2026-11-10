// Жүктемелік сценарий (11-ЗЖ). Талаптар: docs/requirements/nfr.md
//   ФЕТ-01: жазылу беті 50 қызмет пен 300 жазылу базада тұрғанда 1,5 с ішінде ашылады (p95);
//           20 виртуалды пайдаланушы, 3 минут.
//   ФЕТ-02: жазылуды жіберу 2 с ішінде өңделеді (p95).
// Алдын ала: python manage.py demo_derekter --seed 42
// Іске қосу: k6 run tests/load/zhazylu.js   (BASE айнымалысымен басқа мекенжай: -e BASE=http://...)
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE || 'http://localhost:8000';

export const options = {
  vus: 20,
  duration: '3m',
  thresholds: {
    'http_req_duration{name:bet}': ['p(95)<1500'],     // ФЕТ-01
    'http_req_duration{name:jiberu}': ['p(95)<2000'],  // ФЕТ-02
    checks: ['rate>0.99'],
  },
};

export function setup() {
  const ids = [...http.get(`${BASE}/`).body.matchAll(/\/zhazylu\/(\d+)\//g)].map((m) => m[1]);
  if (!ids.length) throw new Error('Қызмет жоқ: алдымен demo_derekter командасын іске қосыңыз');
  return { ids };
}

export default function (data) {
  const service = data.ids[Math.floor(Math.random() * data.ids.length)];
  const day = new Date(Date.now() + (1 + Math.floor(Math.random() * 13)) * 86400000)
    .toISOString().slice(0, 10);
  const page = http.get(`${BASE}/zhazylu/${service}/?kun=${day}`, { tags: { name: 'bet' } });
  check(page, { 'бет ашылды (200)': (r) => r.status === 200 });

  const slots = [...page.body.matchAll(/name="start" value="([^"]+)"/g)].map((m) => m[1]);
  const csrf = page.body.match(/name="csrfmiddlewaretoken" value="([^"]+)"/);
  // Бос уақыт таусылса да, жіберу өңделуі керек: бос емес уақытқа жібереміз (жүйе бас тартады)
  const start = slots.length ? slots[Math.floor(Math.random() * slots.length)] : `${day}T10:00:00+05:00`;
  if (csrf) {
    const res = http.post(`${BASE}/zhazylu/${service}/?kun=${day}`, {
      csrfmiddlewaretoken: csrf[1],
      start,
      client_name: `Жүктеме ${__VU}-${__ITER}`,
      client_phone: '+77000000000',
      consent: 'on',
    }, { tags: { name: 'jiberu' }, redirects: 0, headers: { Referer: `${BASE}/` } });
    // 302 — жазылды; 200 — уақытты басқа виртуалды пайдаланушы алып қойды (бұл да дұрыс жауап)
    check(res, { 'жіберу өңделді (302/200)': (r) => r.status === 302 || r.status === 200 });
  }
  sleep(1);
}
