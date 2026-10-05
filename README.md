# RADIUS Manager

Web app จัดการ FreeRADIUS ผ่านฐานข้อมูล MariaDB — ดูสเปกเต็มใน [CLAUDE.md](./CLAUDE.md)

**สถานะปัจจุบัน:** MVP ครบทุก phase ตาม `CLAUDE.md` หัวข้อ 10 (ข้อ 0–7) — Auth, Users,
Groups, NAS, Traffic Shaping (MikroTik + UniFi via Filter-Id), Accounting, Online Sessions (PoD/CoA),
Auth Log, Dashboard, Audit Log, Settings, i18n ไทย/อังกฤษ

> ⚠️ โค้ดชุดนี้เขียนจากเครื่อง dev ที่ไม่มี Python/Node/Docker และไม่มีทางเข้าเครื่อง
> Linux เป้าหมายจริง (ดู [docs/decisions.md](./docs/decisions.md)) — **อัปเดต
> 2026-10-06**: ตอนนี้รันจริงบนเครื่องเป้าหมายแล้วผ่าน Docker ([docker-compose.app.yml](./docker-compose.app.yml))
> login ใช้งานได้จริง แต่ยังไม่ได้รัน lint + test suite เต็ม (`ruff`/`mypy`/`pytest`/
> `eslint`/`vitest`) บนเครื่องจริง และยังไม่ได้ทดสอบ PoD/CoA กับ MikroTik จริง
> (ดู TODO ใน [docs/environment.md](./docs/environment.md))

## วิธีรัน (manual หรือ Docker — ไม่ใช้ systemd / nginx ของเครื่องจริง)

### 0. เตรียม environment
```bash
cp .env.example backend/.env
cp .env.example frontend/.env   # frontend อ่านเฉพาะตัวแปรที่ขึ้นต้นด้วย VITE_
```
แก้ `backend/.env`: ใส่ `DB_PASSWORD` จริง, เปลี่ยน `APP_SECRET_KEY` และตรวจค่าที่ยังเป็น
TODO ใน [docs/environment.md](./docs/environment.md) (FreeRADIUS version/path, IP เครื่อง)

ถ้ายังไม่มี DB user `radius_web` ให้รัน (แก้รหัสผ่านใน SQL ก่อน):
```bash
mysql -u root -p < scripts/create-db-user.sql
```

### 1. Back-end → http://<host>:8001
```bash
./scripts/run-backend.sh
# หรือรันเองทีละขั้น:
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head        # สร้างตาราง app_* + seed bandwidth profile preset
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
ตรวจว่าใช้งานได้: `curl http://localhost:8001/health` และเปิด Swagger ที่
`http://localhost:8001/docs`

รันค้างไว้: `tmux new -s radius-api` หรือ `nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 > logs/api.log 2>&1 &`

**สร้าง admin คนแรก** (ต้องทำก่อนถึงจะ login ได้ — ไม่มีระบบ self-register):
```bash
cd backend && source .venv/bin/activate
python -m app.cli.create_admin --username admin --role admin
```

### 2. Front-end → http://<host>:5174
```bash
./scripts/run-frontend.sh
# หรือ
cd frontend
npm install
npm run dev
```
เปิด `http://localhost:5174` แล้ว login ด้วย admin ที่สร้างไว้

### Feature flags สำหรับ MikroTik (backend/.env)
| ตัวแปร | ผล |
|---|---|
| `ENABLE_POD=true` | เปิดปุ่ม Disconnect ในหน้า Online Sessions (ส่ง Disconnect-Request ผ่าน `radclient`) |
| `ENABLE_COA=true` | เปิดปุ่ม Change speed (ส่ง CoA เปลี่ยน `Mikrotik-Rate-Limit`) |
| `RADCLIENT_PATH` | path ของ `radclient` (ตรวจด้วย `which radclient`) |
| `RADIUS_DYNAUTH_PORT` | port ที่ MikroTik รับ PoD/CoA (ค่าเริ่มต้น 3799) |
| `ONLINE_SESSIONS_EXCLUDE_USERNAMES` | RADIUS username ที่ซ่อนจากหน้า Online Sessions (คั่นด้วย comma) — ใช้ซ่อน account ที่ไม่ใช่ลูกค้าจริง เช่น PPPoE ของ office ที่ admin ใช้ต่อเน็ตเข้าเว็บนี้เอง |

MikroTik ต้องตั้ง `/radius incoming set accept=yes port=3799` และ secret ต้องตรงกับตาราง `nas`
(หน้า NAS ในเว็บแสดงคำสั่งนี้ไว้ให้)

### Dev นอกเครื่องเป้าหมายจริง (ไม่มี FreeRADIUS/MariaDB จริงให้เชื่อม)
```bash
docker compose -f docker-compose.dev.yml up -d
```
ใช้ MariaDB local สำหรับ dev/test เท่านั้น — ต้องเติม
[docs/freeradius-schema.sql](./docs/freeradius-schema.sql) ด้วย schema จริงก่อน
(ปัจจุบันยังเป็น placeholder)

### รันด้วย Docker (ทางเลือกแทนขั้นตอน manual ด้านบน — backend/frontend เท่านั้น)
Containerize เฉพาะ backend กับ frontend สอง service นี้ — MariaDB/FreeRADIUS/nginx
ยังเป็นของเดิมบนเครื่องจริงเหมือนเดิมทุกประการ (ดู [docker-compose.app.yml](./docker-compose.app.yml))
ใช้ได้เฉพาะบน Linux host จริง (ใช้ `network_mode: host` เพื่อให้คอนเทนเนอร์เข้าถึง
MariaDB ที่ bind `localhost` และ MikroTik บน LAN ได้ตรงๆ — **ใช้ไม่ได้กับ Docker
Desktop บน macOS/Windows**)

```bash
cp .env.example backend/.env   # แก้ DB_PASSWORD, APP_SECRET_KEY ฯลฯ ให้เรียบร้อยก่อน

docker compose -f docker-compose.app.yml build
docker compose -f docker-compose.app.yml up -d
```

**สร้าง admin คนแรก** (ต้องรันผ่าน `docker compose exec` เพราะรันในคอนเทนเนอร์):
```bash
docker compose -f docker-compose.app.yml exec backend \
  python -m app.cli.create_admin --username admin --role admin
```

ข้อควรรู้:
- `frontend/nginx.conf` proxy `/api/` ไปที่ backend บน `127.0.0.1:8001` ให้เอง
  (ใช้ได้เพราะ `network_mode: host`) และ `VITE_API_BASE_URL` default เป็น
  relative path `/api/v1` — แปลว่า image เดียวกันใช้ได้ทุก host/IP/port โดยไม่ต้อง
  build ใหม่ (ไม่ต้องใส่ `--build-arg` อีกต่อไป) ใส่ `--build-arg
  VITE_API_BASE_URL=...` เฉพาะกรณีต้องการให้ frontend เรียก backend คนละที่กับที่
  nginx ของมันเอง proxy ให้
- backend รัน `alembic upgrade head` อัตโนมัติทุกครั้งที่ container เริ่ม (ดู
  `backend/docker-entrypoint.sh`) เหมือนขั้นตอน manual ด้านบนทุกประการ
- nginx ที่ serve static ไฟล์ของ frontend เป็นคนละตัวกับ nginx ของเครื่องจริง —
  ไม่แตะ `/etc/nginx` บนเครื่องจริงเลย

## หน้าจอ
Dashboard · Users (+ หน้ารายละเอียด: ข้อมูล / Reply attributes / Traffic shaping ที่มีผลจริง /
Sessions / Auth log) · Groups · Bandwidth Profiles (builder + live preview + apply) · NAS ·
Online Sessions (tab ทั้งหมด/PPPoE/Hotspot, refresh ทุก 15 วิ) · Accounting (+ export CSV) ·
Auth Log · Audit Log · Settings (เปลี่ยนรหัสผ่าน, สลับภาษา)

Role `viewer` เห็นทุกหน้าแต่ไม่มีปุ่มแก้ไข (backend บังคับสิทธิ์อีกชั้น)

## Ports
- Backend: **8001**
- Frontend (vite dev server): **5174**
- ห้ามใช้ 1812/1813/3799 (FreeRADIUS / MikroTik ใช้อยู่)

## Testing
```bash
# Backend (unit test ไม่ต้องใช้ DB: shaping, radclient, classifier, utils)
cd backend && ruff check . && mypy . && pytest

# Frontend
cd frontend && npm run lint && npm run typecheck && npm test
```

## เอกสารเพิ่มเติม
- [docs/api.md](./docs/api.md) — สรุป endpoint ทั้งหมด
- [docs/environment.md](./docs/environment.md) — ค่าที่สำรวจได้จากเครื่องจริง (มี TODO ค้างอยู่)
- [docs/decisions.md](./docs/decisions.md) — บันทึกการตัดสินใจที่สเปกไม่ได้ระบุไว้
- [CLAUDE.md](./CLAUDE.md) — สเปกเต็มของโปรเจกต์และแผนการทำงาน
