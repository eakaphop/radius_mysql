# RADIUS Manager — Project Spec สำหรับ Claude

เอกสารนี้เป็น instruction หลักให้ Claude ใช้สร้างและพัฒนา Web Application สำหรับ
**จัดการ FreeRADIUS ผ่านฐานข้อมูล MariaDB** โดยแยกโค้ดเป็น **Back-end (REST API)** และ
**Front-end (SPA)** อย่างชัดเจน อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง และทำตาม convention ที่ระบุไว้

---

## 1. ภาพรวมโครงการ

- FreeRADIUS ทำงานอยู่แล้วโดยใช้ `rlm_sql` เชื่อมกับ MariaDB (schema มาตรฐานของ FreeRADIUS 3.x)
- Web app นี้ **ไม่แตะ config ของ FreeRADIUS** แต่จัดการข้อมูลในตาราง SQL ที่ FreeRADIUS อ่านอยู่แล้ว
- ผู้ใช้งาน web app คือ **ผู้ดูแลระบบ (admin)** ไม่ใช่ end user ของ RADIUS
- ต้องใช้งานได้ทั้งภาษาไทยและอังกฤษ (i18n) ค่าเริ่มต้นเป็นภาษาไทย

### ฟีเจอร์ที่ต้องมี (MVP)

| หมวด | รายละเอียด |
|---|---|
| Dashboard | จำนวน user ทั้งหมด, user ที่ online อยู่, auth สำเร็จ/ล้มเหลว 24 ชม., ปริมาณ traffic รายวัน |
| RADIUS Users | CRUD ผู้ใช้ (`radcheck` / `radreply`), กำหนดรหัสผ่าน, กำหนด group, เลือก service type (PPPoE / Hotspot), เปิด/ปิดใช้งาน, วันหมดอายุ, ค้นหา/กรอง/แบ่งหน้า |
| Groups | CRUD group (`radgroupcheck` / `radgroupreply`), กำหนด attribute เช่น `Simultaneous-Use`, `Session-Timeout`, `Mikrotik-Rate-Limit`, `Framed-IP-Address` |
| Traffic Shaping (MikroTik) | สร้าง **Bandwidth Profile** ด้วย visual builder (down/up, burst, priority, min-rate, quota, address-list) แล้วแปลงเป็น `Mikrotik-Rate-Limit` และ VSA อื่นๆ ลง `radgroupreply` / `radreply`; override รายคนได้; ส่ง CoA ปรับความเร็ว session ที่ online อยู่ (ดูหัวข้อ 6.1) |
| NAS Clients | CRUD ตาราง `nas` (shortname, nasname/IP, secret, type, description) |
| Accounting | ดู `radacct` แบบ list + filter (username, NAS, ช่วงเวลา), รายละเอียด session, export CSV |
| Online Sessions | session ที่ `acctstoptime IS NULL` แยก tab PPPoE / Hotspot, ปุ่มบังคับ disconnect และ CoA เปลี่ยนความเร็ว (ส่งผ่าน `radclient` — มี flag เปิด/ปิด) |
| Auth Log | ดู `radpostauth` (username, reply, authdate, NAS) พร้อม filter |
| Admin Auth | login ด้วยตาราง `admin_users` ของ web app เอง (ไม่ใช่ radcheck), JWT access + refresh token, role `admin` / `viewer` |
| Audit Log | บันทึกทุกการเปลี่ยนแปลงข้อมูล (ใคร, ทำอะไร, กับ record ไหน, เมื่อไร) ลงตาราง `audit_log` |

### สิ่งที่ไม่ต้องทำใน MVP
- Self-service portal สำหรับ end user
- Billing / voucher / hotspot captive portal
- Multi-tenant

---

## 2. Tech Stack

### Back-end (`/backend`)
- **Python 3.12 + FastAPI**
- **SQLAlchemy 2.x (async) + `asyncmy`** เป็น driver MariaDB
- **Alembic** สำหรับ migration เฉพาะตารางของ web app (`admin_users`, `audit_log`, `refresh_tokens`) — **ห้าม** สร้าง migration ที่แก้ตาราง FreeRADIUS เดิม
- **Pydantic v2** สำหรับ schema / validation
- **python-jose** (JWT) + **passlib[bcrypt]** สำหรับ admin password
- **pytest + httpx** สำหรับ test
- Lint/format: **ruff**, type check: **mypy**

### Front-end (`/frontend`)
- **React 18 + TypeScript + Vite**
- **Tailwind CSS** + **shadcn/ui** สำหรับ component
- **TanStack Query** สำหรับ data fetching / cache
- **TanStack Table** สำหรับตารางที่มี sort/filter/pagination
- **React Router v6**
- **react-hook-form + zod** สำหรับฟอร์ม
- **i18next** สำหรับ th/en
- **Recharts** สำหรับกราฟใน dashboard
- Lint/format: **eslint + prettier**

### Infrastructure (สภาพแวดล้อมที่มีอยู่แล้วบนเครื่อง — ห้ามติดตั้งซ้ำ)
บนเครื่องเป้าหมายมีสิ่งเหล่านี้ติดตั้งและทำงานอยู่แล้ว ให้ **ใช้ของเดิม** ไม่ต้องใช้ Docker สำหรับ service เหล่านี้:

| Service | สถานะ | สิ่งที่ Claude ต้องทำ |
|---|---|---|
| **MariaDB** | ติดตั้งแล้ว มี database ของ FreeRADIUS อยู่แล้ว | เชื่อมต่อผ่าน `127.0.0.1` หรือ unix socket; สร้าง DB user แยกสำหรับ web app ถ้าจำเป็น |
| **FreeRADIUS** | ติดตั้งและใช้ `rlm_sql` กับ MariaDB อยู่แล้ว | **ห้ามแก้ config** ยกเว้นผู้ใช้สั่ง; อ่าน `mods-available/sql` เพื่อหา DB name / user / ชื่อตาราง |
| **nginx** | ติดตั้งแล้ว มี site อื่นใช้งานอยู่ | **ห้ามแตะ** ในขอบเขตงานนี้ (ยังไม่ทำ reverse proxy) |
| **Let's Encrypt (certbot)** | มี cert อยู่แล้ว | **ห้ามแตะ** ในขอบเขตงานนี้ |

### วิธีรัน (manual — ไม่ใช้ systemd / Docker / nginx)
ทั้งสองฝั่งรันด้วยมือในคนละ terminal บนเครื่องเดียวกัน:

```bash
# Back-end  → http://<host>:8001
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Front-end → http://<host>:5174
cd frontend
npm run dev            # vite.config.ts ตั้ง server.port = 5174, server.host = true
```

- **Back-end port 8001** (ไม่ใช้ 8000 เพื่อเลี่ยงชนกับ service อื่น) — `--host 0.0.0.0` เพื่อให้เข้าจากเครื่องอื่นใน LAN ได้
- **Front-end port 5174** (vite dev server) เรียก API ตรงไปที่ `http://<host>:8001/api/v1`
- `CORS_ORIGINS` ของ backend ต้องมี `http://localhost:5174` และ IP ของเครื่องที่ port 5174
- ไม่ต้องสร้าง systemd unit หรือ nginx config ในขอบเขตนี้ — ถ้าอยากรันค้างไว้แบบ manual ให้ใช้ `tmux` / `screen` / `nohup` และบอกวิธีในหน้า README
- Front-end และ back-end ต้อง **แยกกันได้อิสระ** สื่อสารกันผ่าน REST API เท่านั้น (ไว้ทำ production deploy ทีหลัง)
- **อัปเดต 2026-10-05**: มี `backend/Dockerfile` และ `frontend/Dockerfile` แล้ว (containerize เฉพาะสอง service นี้ — MariaDB/FreeRADIUS/nginx ของเครื่องจริงยังไม่แตะ ตาม "Infrastructure" ด้านบน) ดูวิธีใช้ใน `docker-compose.app.yml` — รัน manual ตามเดิมก็ยังใช้ได้ปกติ เลือกอย่างใดอย่างหนึ่ง

### ขั้นตอนสำรวจสภาพแวดล้อมก่อนเริ่มงาน (ทำก่อน scaffold เสมอ)
```bash
# FreeRADIUS: หา DB connection ที่ใช้อยู่
grep -E "^\s*(server|port|login|password|radius_db|dialect)" /etc/freeradius/3.0/mods-available/sql   # Debian/Ubuntu
# หรือ /etc/raddb/mods-available/sql บน RHEL/Rocky
freeradius -v          # หรือ radiusd -v เพื่อดู version

# MariaDB: ตรวจตารางที่มี
mysql -u root -p -e "SHOW DATABASES; USE radius; SHOW TABLES; SHOW CREATE TABLE radcheck\G"

# ตรวจว่า port 8001 / 5174 ว่าง
ss -lntp | grep -E ':(8001|5174)'
```
บันทึกค่าที่พบ (DB name, DB user, FreeRADIUS version, path ของ config, IP ของเครื่อง)
ลงใน `docs/environment.md` แล้วใช้ค่าเหล่านั้นใน `.env` — **ห้ามเดา** ถ้าหาไม่พบให้ถามผู้ใช้

### ค่าที่ทราบแล้วจากเครื่องจริง (จาก `mods-available/sql`)
| รายการ | ค่า |
|---|---|
| MariaDB server | `localhost:3306` |
| Database | `radius` |
| DB user ที่ FreeRADIUS ใช้ | `radius` (รหัสผ่านอยู่ใน `mods-available/sql` — **ห้ามคัดลอกลง repo หรือ docs**, ใส่ใน `.env` บนเครื่องเท่านั้น) |
| ยังไม่ทราบ | FreeRADIUS version และ path config (Debian `/etc/freeradius/3.0` หรือ RHEL `/etc/raddb`), IP ของเครื่อง |

- แนะนำให้สร้าง DB user แยก `radius_web` สำหรับ web app (หัวข้อ 7) แต่ถ้าผู้ใช้ต้องการใช้ user `radius` เดิมก็ทำได้ โดย `DB_USER=radius`
- ⚠️ ในไฟล์ sql ที่ดู มีบรรทัด `radius_db = "(DESCRIPTION=...` (Oracle) ที่ดูเหมือนไม่ได้ comment `#` ไว้ — ให้ตรวจสอบและแจ้งผู้ใช้ก่อน ไม่แก้เอง

---

## 3. โครงสร้าง Repository

```
radius-manager/
├── CLAUDE.md                 # ไฟล์นี้
├── README.md                 # วิธีรัน manual (backend 8001, frontend 5174)
├── .env.example
├── scripts/
│   ├── create-db-user.sql    # สร้าง DB user ของ web app (grant เฉพาะที่จำเป็น)
│   ├── run-backend.sh        # activate venv + uvicorn --port 8001
│   └── run-frontend.sh       # npm run dev (port 5174)
├── docs/
│   ├── environment.md        # ค่าที่สำรวจได้จากเครื่องจริง (DB, domain, path)
│   ├── api.md                # สรุป endpoint (สร้างจาก OpenAPI)
│   └── freeradius-schema.sql # schema อ้างอิงของ FreeRADIUS (read-only reference)
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   ├── app/
│   │   ├── main.py           # สร้าง FastAPI app, register routers, CORS
│   │   ├── core/
│   │   │   ├── config.py     # Settings จาก env (pydantic-settings)
│   │   │   ├── security.py   # JWT, password hashing
│   │   │   └── deps.py       # dependencies: get_db, get_current_admin, require_role
│   │   ├── db/
│   │   │   ├── session.py    # async engine + session factory
│   │   │   └── models/       # SQLAlchemy models (แยกไฟล์ต่อตาราง)
│   │   ├── schemas/          # Pydantic schemas (แยกไฟล์ต่อ resource)
│   │   ├── services/         # business logic (ไม่มี FastAPI import ในชั้นนี้)
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── groups.py
│   │   │       ├── nas.py
│   │   │       ├── accounting.py
│   │   │       ├── sessions.py
│   │   │       ├── postauth.py
│   │   │       ├── dashboard.py
│   │   │       └── audit.py
│   │   └── utils/
│   └── tests/
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── src/
    │   ├── main.tsx
    │   ├── app/              # router, providers, layout
    │   ├── api/              # client ที่ generate/เขียนตาม OpenAPI + hooks ของ TanStack Query
    │   ├── features/         # แยกตาม domain
    │   │   ├── auth/
    │   │   ├── dashboard/
    │   │   ├── users/
    │   │   ├── groups/
    │   │   ├── nas/
    │   │   ├── accounting/
    │   │   ├── sessions/
    │   │   ├── postauth/
    │   │   └── audit/
    │   ├── components/       # component ใช้ร่วม (ui/, layout/, data-table/)
    │   ├── lib/              # utils, formatters (bytes, duration, datetime)
    │   └── locales/
    │       ├── th/
    │       └── en/
    └── tests/
```

---

## 4. ฐานข้อมูล

### 4.1 ตาราง FreeRADIUS (มีอยู่แล้ว — อ่าน/เขียนข้อมูลได้ แต่ห้ามแก้โครงสร้าง)

| ตาราง | ใช้ทำอะไร | หมายเหตุ |
|---|---|---|
| `radcheck` | attribute ตรวจสอบต่อ user (รหัสผ่าน, Expiration) | รหัสผ่านเก็บเป็น `Cleartext-Password` โดยค่าเริ่มต้น รองรับ `SSHA-Password` / `NT-Password` ผ่าน setting |
| `radreply` | attribute ตอบกลับต่อ user | เช่น `Framed-IP-Address` |
| `radusergroup` | ผูก user กับ group (`priority`) | |
| `radgroupcheck` | attribute ตรวจสอบต่อ group | เช่น `Simultaneous-Use` |
| `radgroupreply` | attribute ตอบกลับต่อ group | เช่น `Mikrotik-Rate-Limit`, `Session-Timeout` |
| `radacct` | accounting record | ตารางใหญ่ — ทุก query ต้องมี index-friendly filter และ pagination |
| `radpostauth` | log ผลการ auth | |
| `nas` | NAS client (FreeRADIUS โหลดตอน start / ผ่าน `radmin`) | หลังแก้ต้องแจ้งเตือน admin ว่าอาจต้อง reload FreeRADIUS |

ใช้ schema จาก `raddb/mods-config/sql/main/mysql/schema.sql` ของ FreeRADIUS 3.x เป็นอ้างอิง
(วางสำเนาไว้ที่ `docs/freeradius-schema.sql`)

**กฎสำคัญเรื่อง `radcheck`:**
- "user 1 คน" = ชุด row ใน `radcheck` ที่มี `username` เดียวกัน ไม่มีตาราง user จริง
- การ "ปิดใช้งาน user" ให้ทำโดยเพิ่ม row `Auth-Type := Reject` ไม่ใช่ลบรหัสผ่าน
- วันหมดอายุใช้ attribute `Expiration` รูปแบบ `"23 Sep 2026 23:59"` (format ที่ FreeRADIUS ต้องการ)
- การลบ user ต้องลบจาก `radcheck`, `radreply`, `radusergroup` ใน transaction เดียว (ไม่ลบ `radacct` / `radpostauth`)

### 4.2 ตารางของ web app (สร้างผ่าน Alembic, ใช้ prefix `app_`)

```sql
app_admin_users     (id, username, password_hash, role ENUM('admin','viewer'), is_active, created_at, last_login_at)
app_refresh_tokens  (id, admin_id, token_hash, expires_at, revoked_at)
app_audit_log       (id, admin_id, action, resource_type, resource_id, before_json, after_json, ip_address, created_at)
app_bandwidth_profiles (id, name, service_type ENUM('pppoe','hotspot','both'), description,
                        download_kbps, upload_kbps, burst_download_kbps, burst_upload_kbps,
                        burst_threshold_download_kbps, burst_threshold_upload_kbps, burst_time_sec, priority,
                        min_download_kbps, min_upload_kbps, session_timeout_sec, idle_timeout_sec,
                        simultaneous_use, mikrotik_group, framed_pool,
                        total_quota_bytes, address_list, is_active, created_at, updated_at)
```

---

## 5. Back-end API Spec

Base path: `/api/v1` — ทุก endpoint (ยกเว้น `/auth/login`, `/auth/refresh`, `/health`) ต้องมี
`Authorization: Bearer <access_token>` และ endpoint ที่แก้ไขข้อมูลต้องมี role `admin`

### รูปแบบ response มาตรฐาน

```json
// สำเร็จ (list)
{ "items": [...], "total": 123, "page": 1, "page_size": 25 }

// error
{ "detail": "ข้อความ", "code": "USER_NOT_FOUND" }
```

### Endpoints

**Auth**
- `POST /auth/login` → `{access_token, refresh_token, admin: {...}}`
- `POST /auth/refresh`
- `POST /auth/logout` (revoke refresh token)
- `GET  /auth/me`

**Users** (รวม view จาก radcheck + radreply + radusergroup)
- `GET    /users?search=&group=&status=active|disabled|expired&page=&page_size=&sort=`
- `GET    /users/{username}`
- `POST   /users` body: `{username, password, groups[], expiration?, reply_attributes[]?}`
- `PUT    /users/{username}`
- `PATCH  /users/{username}/password`
- `PATCH  /users/{username}/status` body: `{enabled: bool}`
- `DELETE /users/{username}`
- `GET    /users/{username}/sessions` (radacct ของ user นี้)

**Groups**
- `GET/POST /groups`, `GET/PUT/DELETE /groups/{groupname}`
- `GET /groups/{groupname}/members`
- body ของ group: `{groupname, check_attributes: [{attribute, op, value}], reply_attributes: [...]}`

**NAS**
- `GET/POST /nas`, `GET/PUT/DELETE /nas/{id}`
- response หลังแก้ไขต้องมี `"warning": "FreeRADIUS reload required"`

**Accounting**
- `GET /accounting?username=&nasipaddress=&from=&to=&page=&page_size=`
- `GET /accounting/{radacctid}`
- `GET /accounting/export?...` → CSV stream

**Sessions**
- `GET  /sessions/online`
- `POST /sessions/{radacctid}/disconnect` (ทำงานเมื่อ `ENABLE_POD=true` เท่านั้น ไม่งั้นตอบ 501)
- `POST /sessions/{radacctid}/coa` body: `{profile_id}` หรือ `{rate_limit: "..."}` — ส่ง CoA เปลี่ยนความเร็วทันที (ต้อง `ENABLE_COA=true`)

**Traffic Shaping (MikroTik)**
- `GET/POST /shaping/profiles`, `GET/PUT/DELETE /shaping/profiles/{id}`
- `POST /shaping/preview` body: profile fields → ตอบ `{attributes: [{attribute, op, value}], rate_limit_string}` (ไม่บันทึก ใช้แสดง live preview ในฟอร์ม)
- `POST /shaping/profiles/{id}/apply` body: `{target: "group"|"user", name}` → เขียน attribute ลง `radgroupreply` หรือ `radreply` (ลบ attribute เดิมของชุด shaping ก่อนแล้วเขียนใหม่ใน transaction เดียว)
- `GET  /shaping/profiles/{id}/targets` → group/user ที่ใช้ profile นี้
- `POST /shaping/parse` body: `{rate_limit: "10M/20M 20M/40M ..."}` → แยกเป็น field (ใช้ import ค่าเดิมที่มีอยู่ใน DB เข้าฟอร์ม)

**Post-auth log**
- `GET /postauth?username=&reply=Access-Accept|Access-Reject&from=&to=&page=`

**Dashboard**
- `GET /dashboard/summary`
- `GET /dashboard/traffic?days=7`
- `GET /dashboard/auth-stats?hours=24`

**Audit**
- `GET /audit?admin=&resource_type=&from=&to=&page=`

**Health**
- `GET /health` → ตรวจว่าเชื่อม DB ได้

### กฎการเขียน back-end
- Router บาง → เรียก service; service ทำ business logic + transaction; ห้ามเขียน SQL ใน router
- ทุก write operation ต้อง `async with session.begin()` และเขียน `app_audit_log` ในธุรกรรมเดียวกัน
- Validate attribute name / operator ตาม dictionary ของ RADIUS ที่กำหนดใน `app/utils/radius_attrs.py`
  (ทำเป็น whitelist ที่ขยายได้ ไม่ใช่ hardcode ใน schema)
- Operator ที่รองรับ: `:=`, `==`, `=`, `+=`, `!=`, `>`, `>=`, `<`, `<=`, `=~`, `!~`, `=*`, `!*`
- Pagination สูงสุด `page_size=200`
- ห้าม log รหัสผ่านหรือ NAS secret ลง log / audit (mask เป็น `***`)
- Type hint ครบทุก function, docstring สั้นๆ เป็นภาษาอังกฤษ

---

## 6. Front-end Spec

### หน้าจอ
1. **Login**
2. **Dashboard** — card สรุป 4 ใบ + กราฟ traffic 7 วัน + กราฟ auth accept/reject 24 ชม. + ตาราง online ล่าสุด 10 รายการ
3. **Users** — DataTable (search, filter group/status, sort, pagination), drawer/dialog สำหรับ create/edit, badge สถานะ (Active / Disabled / Expired)
4. **User detail** — tab: ข้อมูล, Reply attributes, Sessions ล่าสุด, Auth log
5. **Groups** — list + form แก้ attribute แบบ key-op-value editor (เพิ่ม/ลบแถวได้)
6. **NAS** — list + form, แสดง warning หลังบันทึก
6b. **Bandwidth Profiles** — list + builder form (ดูหัวข้อ 6.1): slider/input download-upload, toggle Burst, priority 1–8, min-rate, quota, address-list, live preview ของ `Mikrotik-Rate-Limit` string, ปุ่ม Apply to group/user, แสดงว่ามีใครใช้ profile นี้อยู่
7. **Accounting** — ตาราง + filter ช่วงวันที่ + ปุ่ม Export CSV
8. **Online Sessions** — tab ทั้งหมด / PPPoE / Hotspot, auto-refresh ทุก 15 วินาที, ปุ่ม Disconnect และ Change speed (CoA) — ซ่อนถ้า feature ปิด
9. **Auth Log**
10. **Audit Log**
11. **Settings** (เปลี่ยนรหัสผ่าน admin, สลับภาษา)

### กฎการเขียน front-end
- แยก **API layer** (`src/api`) ออกจาก UI ทั้งหมด component ห้าม `fetch` ตรง
- Access token เก็บใน memory, refresh token ใน `httpOnly` cookie (backend ตั้งค่า) — **ห้าม** ใช้ `localStorage` เก็บ token
- ทุกข้อความที่ผู้ใช้เห็นต้องผ่าน `t('...')` ของ i18next ห้าม hardcode string
- แสดง bytes เป็น human-readable (KB/MB/GB) และเวลาเป็น timezone ของ browser
- Form ทุกอันใช้ zod schema ที่ตรงกับ Pydantic schema ฝั่ง backend
- Loading / empty / error state ต้องมีทุกตาราง
- Responsive ขั้นต่ำ 1024px (desktop-first) แต่ต้องไม่พังบน tablet

---

## 6.1 Traffic Shaping สำหรับ MikroTik

MikroTik (PPPoE / Hotspot / IPsec) รับค่าจำกัดความเร็วจาก RADIUS ผ่าน Vendor-Specific Attributes (vendor id 14988)
FreeRADIUS 3.x มี `dictionary.mikrotik` อยู่แล้ว ไม่ต้องเพิ่ม dictionary เอง

### Attribute ที่ต้องรองรับใน builder

| Attribute | ใช้ทำอะไร | หมายเหตุ |
|---|---|---|
| `Mikrotik-Rate-Limit` | จำกัดความเร็วหลัก (สร้าง simple queue ให้อัตโนมัติ) | รูปแบบด้านล่าง |
| `Mikrotik-Address-List` | ใส่ IP ของ user เข้า address-list (ใช้ทำ firewall/mangle ต่อ) | เช่น `premium`, `blocked` |
| `Mikrotik-Total-Limit` + `Mikrotik-Total-Limit-Gigawords` | โควตาปริมาณรวม (bytes) หมดแล้วตัด session | `Total-Limit` = low 32 bit, `Gigawords` = high 32 bit — backend ต้องคำนวณแยกให้ |
| `Mikrotik-Recv-Limit` / `Mikrotik-Xmit-Limit` (+ `-Gigawords`) | โควตาแยก upload / download | optional |
| `Mikrotik-Group` | Hotspot user profile / PPP profile บน router | ใช้แทนการตั้ง rate-limit ตรงถ้าอยากจัดการ queue ฝั่ง router |
| `Session-Timeout`, `Idle-Timeout` | ตัด session ตามเวลา | standard attribute |
| `Acct-Interim-Interval` | ความถี่ interim accounting (วินาที) | แนะนำ 300 เพื่อให้ dashboard/quota แม่นขึ้น |
| `WISPr-Bandwidth-Max-Down` / `WISPr-Bandwidth-Max-Up` | ทางเลือกสำหรับ Hotspot (bps) | ใส่คู่กับ Rate-Limit ได้ MikroTik ให้ Rate-Limit มีลำดับสูงกว่า |

### รูปแบบ `Mikrotik-Rate-Limit`

```
rx-rate[/tx-rate] [rx-burst-rate[/tx-burst-rate] [rx-burst-threshold[/tx-burst-threshold] [rx-burst-time[/tx-burst-time] [priority] [rx-rate-min[/tx-rate-min]]]]]
```

- **rx = ทิศทางที่ router รับจาก client = Upload ของผู้ใช้**, **tx = Download ของผู้ใช้** — UI ต้องแสดงเป็น "Download / Upload" แต่ตอนประกอบ string ต้องเรียง `upload/download` (สาเหตุ bug บ่อยที่สุด ต้องมี unit test)
- หน่วย: `k` (kbps) และ `M` (Mbps) ตัวเลขล้วน = bps; backend เก็บเป็น kbps แล้วแปลงตอนประกอบ (ใช้ `M` เมื่อหารด้วย 1000 ลงตัว)
- priority 1 (สูงสุด) – 8 (ต่ำสุด), ค่าเริ่มต้น 8
- ทุกส่วนหลัง rate หลักเป็น optional แต่ **ถ้าใส่ส่วนหลัง ต้องใส่ส่วนก่อนหน้าให้ครบ** (ใช้ค่า rate หลักแทนถ้าผู้ใช้ไม่กำหนด burst แต่กำหนด priority)
- ตัวอย่างที่ builder ต้องผลิตได้:
  - 20M down / 5M up ไม่มี burst → `5M/20M`
  - 20/5 + burst 40/10 threshold 15/4 เวลา 10 วิ priority 5 → `5M/20M 10M/40M 4M/15M 10/10 5`
  - เพิ่ม min-rate 2M/8M → `5M/20M 10M/40M 4M/15M 10/10 5 2M/8M`

### กฎการ implement
- Logic ประกอบ / แยก string อยู่ที่ `backend/app/services/mikrotik_shaping.py` เพียงที่เดียว ฝั่ง frontend เรียก `/shaping/preview` ไม่ประกอบเอง (กัน logic แตกต่างกัน)
- `parse()` ต้องรับ string ที่มีอยู่ใน DB เดิมได้ทุกแบบ (มี/ไม่มี burst, หน่วยผสม k/M/bps) และ round-trip `parse(build(x)) == x`
- เมื่อ apply profile ให้เขียนด้วย operator `:=` และลบ attribute ในชุด shaping เดิม (`Mikrotik-Rate-Limit`, `Mikrotik-Address-List`, `Mikrotik-Total-Limit*`, `Session-Timeout`, `Idle-Timeout`, `Acct-Interim-Interval`) ก่อน เพื่อไม่ให้ซ้ำ
- **Priority ระหว่าง user กับ group:** ค่าใน `radreply` ของ user จะทับค่าใน `radgroupreply` — UI ต้องแสดง "effective profile" ให้เห็นว่า user คนนี้ได้ค่าจากตัวเองหรือจาก group
- Validate: download/upload > 0, burst ≥ rate, threshold ≤ burst, min-rate ≤ rate, quota เป็นจำนวนเต็ม bytes, address-list ตรง `^[A-Za-z0-9_-]{1,64}$`
- เมื่อ profile ถูกแก้ ให้ถามว่าต้องการ re-apply ไปยัง group/user ทั้งหมดที่ใช้ profile นี้หรือไม่ (ไม่ทำอัตโนมัติ)
- Preset เริ่มต้น (seed): `Basic 10/5`, `Standard 30/10`, `Premium 100/50`, `Unlimited` (ไม่ใส่ Rate-Limit)

### รองรับทั้ง PPPoE และ Hotspot
ระบบนี้ใช้ทั้งสองแบบบน MikroTik เดียวกัน/หลายตัว ดังนั้นทุก user และ profile ต้องระบุ **service type** ได้

- เพิ่มคอลัมน์ `service_type ENUM('pppoe','hotspot','both') DEFAULT 'both'` ใน `app_bandwidth_profiles`
- แยก user ตาม service ด้วย group naming convention: `pppoe-<plan>` และ `hotspot-<plan>` (เช่น `pppoe-standard`, `hotspot-basic`)
  ผู้ใช้ 1 คนอยู่ได้หลาย group แต่ **ควรมี group ที่ให้ shaping เพียง 1 อันต่อ service** — UI ต้องเตือนถ้าซ้อนกัน
- หน้า Users ต้องมี filter และ badge แสดง service type; ดึงจากชื่อ group และจาก `radacct.servicetype` / `nasporttype` ของ session ล่าสุด
- หน้า Online Sessions แยก tab: **ทั้งหมด / PPPoE / Hotspot** (แยกด้วย `radacct.nasporttype`: PPPoE มักเป็น `Virtual`/`Ethernet`, Hotspot เป็น `Wireless-802.11`/`Ethernet` — ให้ใช้ `servicetype` ร่วมด้วย และเก็บกฎการแยกไว้ที่ `services/session_classifier.py` ที่เดียว)

**Attribute ที่ต่างกันระหว่างสอง service:**

| | PPPoE | Hotspot |
|---|---|---|
| Rate limit | `Mikrotik-Rate-Limit` | `Mikrotik-Rate-Limit` (หรือ `WISPr-Bandwidth-Max-Down/Up` เป็น fallback) |
| Profile บน router | `Mikrotik-Group` = ชื่อ PPP profile | `Mikrotik-Group` = ชื่อ Hotspot user profile |
| IP | `Framed-IP-Address` (static) หรือ `Framed-Pool` (จาก pool บน router) | ปกติไม่ต้องกำหนด ให้ DHCP จัดการ |
| จำกัดจำนวนเครื่อง | `Simultaneous-Use` = 1 | `Simultaneous-Use` ตามแพ็กเกจ (มักมากกว่า 1) |
| MAC binding | `Calling-Station-Id` ใน `radcheck` (optional) | `Calling-Station-Id` ใช้ทำ MAC auth / auto-login |
| Idle timeout | มักไม่ตั้ง | ควรตั้ง (`Idle-Timeout` 300–900) |

- ฟอร์ม profile ต้องซ่อน/แสดง field ตาม `service_type` ที่เลือก (เช่น `Framed-Pool` แสดงเฉพาะ PPPoE)
- ตอน apply profile ให้ตรวจว่า target group/user มี service ตรงกับ profile ไหม ถ้าไม่ตรงให้ตอบ 409 พร้อมข้อความอธิบาย
- Preset seed ให้แยกเป็นสองชุด: `pppoe-basic/standard/premium` และ `hotspot-basic/standard/premium` (hotspot ตั้ง `Idle-Timeout` และ `Simultaneous-Use` ต่างกัน)

### CoA / Disconnect กับ MikroTik
- MikroTik ต้องเปิด `/radius incoming set accept=yes port=3799` และใส่ secret ให้ตรงกับตาราง `nas` — ให้แสดงคำสั่งนี้ในหน้า NAS เป็น help text
- Disconnect: `radclient -x <nas_ip>:3799 disconnect <secret>` ส่ง `User-Name`, `Acct-Session-Id`, `Framed-IP-Address`, `NAS-IP-Address` จาก `radacct`
- CoA: `radclient -x <nas_ip>:3799 coa <secret>` ส่ง attribute ระบุ session เหมือน Disconnect + `Mikrotik-Rate-Limit` ใหม่ (และ `Session-Timeout` ถ้ามี) — RouterOS รองรับ CoA บน PPP/Hotspot ตั้งแต่ v6 แต่ให้ทดสอบกับ version จริงและบันทึกผลใน `docs/environment.md`
- รัน `radclient` ผ่าน `asyncio.create_subprocess_exec` (ห้าม shell=True), timeout 5 วินาที, อ่าน `Received Disconnect-ACK` / `CoA-ACK` / `-NAK` จาก output แล้ว map เป็นผลลัพธ์ที่ UI แสดงได้; NAK ให้แสดง `Error-Cause` ที่ router ตอบกลับ
- ทุกครั้งที่ส่ง PoD/CoA บันทึกลง `app_audit_log` พร้อมผลลัพธ์

---

## 7. Environment Variables (`.env.example`)

```env
# Backend (รัน manual: uvicorn --host 0.0.0.0 --port 8001)
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8001
APP_SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:5174,http://127.0.0.1:5174   # เพิ่ม http://<server-ip>:5174 ถ้าเข้าจากเครื่องอื่น

# ใช้ค่าจริงที่พบใน mods-available/sql (ดู docs/environment.md)
DB_HOST=localhost                # ตรงกับ server = "localhost" ใน mods-available/sql
DB_PORT=3306
DB_NAME=radius                   # ตรงกับ radius_db = "radius"
DB_USER=radius_web               # user แยกของ web app (หรือ radius ถ้าใช้ user เดิมของ FreeRADIUS)
DB_PASSWORD=change-me            # ห้ามใส่รหัสจริงใน .env.example

RADIUS_PASSWORD_ATTRIBUTE=Cleartext-Password   # หรือ SSHA-Password / NT-Password
ENABLE_POD=false
ENABLE_COA=false                 # เปิดเมื่อ MikroTik ตั้ง /radius incoming accept=yes แล้ว
RADIUS_DYNAUTH_PORT=3799         # port ที่ MikroTik รับ PoD/CoA
RADCLIENT_PATH=/usr/bin/radclient
RADCLIENT_TIMEOUT_SEC=5
FREERADIUS_CONFIG_DIR=/etc/freeradius/3.0      # อ่านอย่างเดียว

# Frontend (.env ใน frontend/ — vite อ่านเฉพาะตัวแปรที่ขึ้นต้นด้วย VITE_)
VITE_API_BASE_URL=http://localhost:8001/api/v1    # เปลี่ยนเป็น http://<server-ip>:8001/api/v1 ถ้าเข้าจากเครื่องอื่น
VITE_PORT=5174
```

### สิทธิ์ DB user ของ web app (`scripts/create-db-user.sql`)
```sql
CREATE USER 'radius_web'@'localhost' IDENTIFIED BY '...';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.radcheck      TO 'radius_web'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.radreply      TO 'radius_web'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.radusergroup  TO 'radius_web'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.radgroupcheck TO 'radius_web'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.radgroupreply TO 'radius_web'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.nas           TO 'radius_web'@'localhost';
GRANT SELECT                         ON radius.radacct       TO 'radius_web'@'localhost';
GRANT SELECT                         ON radius.radpostauth   TO 'radius_web'@'localhost';
-- ตาราง app_* : ต้องมี CREATE/ALTER สำหรับ Alembic
GRANT ALL PRIVILEGES ON radius.app_admin_users    TO 'radius_web'@'localhost';
GRANT ALL PRIVILEGES ON radius.app_refresh_tokens TO 'radius_web'@'localhost';
GRANT ALL PRIVILEGES ON radius.app_audit_log      TO 'radius_web'@'localhost';
```
(ถ้า MariaDB ไม่ยอม grant บนตารางที่ยังไม่มี ให้ Alembic รันด้วย user ที่มีสิทธิ์ครั้งแรก แล้วค่อย grant)

---

## 7.1 วิธีรันแบบ manual

**Back-end** (`scripts/run-backend.sh`):
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # ครั้งแรกเท่านั้น
pip install -e ".[dev]"
alembic upgrade head                                  # สร้างตาราง app_* (ไม่แตะตาราง FreeRADIUS)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
- ตรวจว่าใช้งานได้: `curl http://localhost:8001/health` และเปิด Swagger ที่ `http://localhost:8001/docs`
- รันค้างไว้ใช้ `tmux new -s radius-api` หรือ `nohup uvicorn ... > logs/api.log 2>&1 &`

**Front-end** (`scripts/run-frontend.sh`):
```bash
cd frontend
npm install            # ครั้งแรกเท่านั้น
npm run dev            # → http://localhost:5174
```

`vite.config.ts` ต้องตั้งค่า:
```ts
server: {
  port: 5174,
  strictPort: true,    // ถ้าพอร์ตไม่ว่างให้ error ไม่ใช่เลื่อนไปพอร์ตอื่น
  host: true,          // ให้เข้าจากเครื่องอื่นใน LAN ได้
}
```

**เรื่องที่ต้องระวังเมื่อรันแยกพอร์ต:**
- เป็น cross-origin (5174 → 8001) ดังนั้น CORS ต้องตั้ง `allow_credentials=True` และระบุ origin แบบเจาะจง (ห้ามใช้ `*` คู่กับ credentials)
- refresh token cookie ตั้งแบบ `httpOnly; SameSite=Lax` ได้บน HTTP ใน LAN; ถ้าเจอปัญหา cookie ไม่ถูกส่งข้ามพอร์ต ให้ใช้ refresh token ใน response body ชั่วคราวสำหรับ dev และบันทึกไว้ใน `docs/decisions.md`
- ถ้าเครื่องเปิด firewall ต้องเปิด 8001 และ 5174 (`firewall-cmd --add-port=8001/tcp` / `ufw allow 8001`) — แสดงคำสั่งให้ผู้ใช้รันเอง
- ห้ามใช้พอร์ต 1812/1813/3799 ที่ FreeRADIUS ใช้อยู่

**ยังไม่อยู่ในขอบเขตงานนี้:** nginx reverse proxy **ของเครื่องจริง**, HTTPS/Let's Encrypt, systemd unit, production build — จะทำในเฟสถัดไป

**อัปเดต 2026-10-05**: Docker image สำหรับ backend/frontend ทำแล้ว (ดู
`docker-compose.app.yml`) — รันเป็น HTTP เท่านั้น (เคยลอง HTTPS ผ่าน container
`caddy` แยกต่างหากแล้วถอดออกเมื่อ 2026-10-06 ตามที่ผู้ใช้ขอ — ดู
`docs/decisions.md`)

---

## 8. Security Requirements

- Admin password: bcrypt (cost ≥ 12)
- Rate limit `POST /auth/login` (5 ครั้ง/นาที/IP)
- ตรวจ role ทุก endpoint ผ่าน dependency ไม่ใช่เช็คใน function body
- Parameterized query เท่านั้น (SQLAlchemy ทำให้อยู่แล้ว — ห้ามใช้ f-string ประกอบ SQL)
- ไม่ส่ง `radcheck.value` ของ password attribute กลับ API ให้ส่งเป็น `has_password: true`
- NAS `secret` ส่งกลับแบบ mask ยกเว้น endpoint `GET /nas/{id}?reveal=true` ที่ต้อง role `admin`
- Security headers ใส่ที่ FastAPI middleware ไปก่อน (X-Frame-Options, X-Content-Type-Options); HSTS/CSP ค่อยทำตอนขึ้น nginx + HTTPS
- ระบบยังรันบน HTTP ใน LAN เท่านั้น — ห้ามเปิดให้เข้าจากอินเทอร์เน็ตจนกว่าจะทำเฟส HTTPS

---

## 9. Testing

- Backend: coverage ≥ 80% ใน `services/` และ `api/`; ใช้ MariaDB จริงใน docker สำหรับ integration test (ไม่ใช้ SQLite เพราะ dialect ต่างกัน)
- Frontend: Vitest + React Testing Library สำหรับ component หลัก; Playwright สำหรับ e2e flow: login → create user → เห็น user ในตาราง → ลบ
- ทุก PR ต้อง `ruff check`, `mypy`, `pytest`, `eslint`, `tsc --noEmit`, `vitest` ผ่าน

---

## 10. แผนการทำงาน (ทำเป็นลำดับ ตรวจสอบก่อนไปขั้นถัดไป)

**✅ สถานะ 2026-10-06: โปรเจกต์เสร็จแล้ว** ข้อ 0–7 ทำครบ และ **ผ่านการรันจริงบนเครื่อง
เป้าหมายแล้ว** (deploy ผ่าน Docker, login ผ่านจริง — ไม่ใช่แค่โค้ดที่เขียนแบบ blind
อีกต่อไป ดู `docs/decisions.md` สำหรับ bug ที่เจอจากการรันจริงและวิธีแก้)

0. ✅ **สำรวจเครื่อง** — รันคำสั่งในหัวข้อ 2 บันทึก `docs/environment.md` และยืนยันกับผู้ใช้ก่อนเขียนโค้ด
1. ✅ **Scaffold** — backend/frontend skeleton, สร้าง DB user `radius_web`, `/health` เชื่อม MariaDB จริงได้ (dev นอกเครื่องใช้ `docker-compose.dev.yml`)
2. ✅ **Auth** — admin_users migration, login/refresh/logout, หน้า Login, protected route
3. ✅ **Users + Groups** — models/services/API/tests ครบ → UI ตาราง + form
4. ✅ **NAS**
4b. ✅ **Traffic Shaping** — `mikrotik_shaping.py` (build/parse + unit test ครบทุก case), profiles CRUD, apply to group/user, UI builder + preview, effective-profile view
5. ✅ **Accounting + Online Sessions + Post-auth** — รวม PoD/CoA ผ่าน `radclient` ทดสอบกับ MikroTik จริง
6. ✅ **Dashboard**
7. ✅ **Audit log + Settings + i18n ครบทุกหน้า** + README วิธีรัน manual **และ Docker** (ดูหัวข้อ 7)

**🛑 ขอบเขตงานปัจจุบันจบที่ข้อ 7 เหมือนเดิม** — ห้ามเริ่มงานเฟสถัดไปเองก่อนได้รับคำสั่ง แม้โปรเจกต์จะ "เสร็จ" แล้วก็ตาม

เฟสถัดไป (ยังไม่ทำ): production hardening, nginx reverse proxy + HTTPS **ของเครื่องจริง**, systemd, production build (rate limit ทำแล้ว ดูหัวข้อ 8; Docker สำหรับ backend/frontend ทำแล้ว แต่ HTTPS ผ่าน container แยกลองแล้วถอดออกตามที่ผู้ใช้ขอ ดูหัวข้อ 7)

---

## 11. Convention ทั่วไปสำหรับ Claude

- ก่อนเขียนโค้ดใหม่ ให้ดูโค้ดที่มีอยู่แล้วในโฟลเดอร์เดียวกันและทำตาม pattern เดิม
- เมื่อเพิ่ม endpoint ใหม่ ต้องเพิ่มทั้ง: model/schema → service → router → test → API hook ฝั่ง frontend → i18n key ทั้ง th และ en
- Commit message ใช้ Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`) ภาษาอังกฤษ
- ถ้าต้องตัดสินใจเรื่องที่ spec ไม่ได้ระบุ ให้เลือกทางที่เรียบง่ายที่สุดและบันทึกเหตุผลไว้ใน `docs/decisions.md`
- ห้ามแก้ตาราง FreeRADIUS เดิม, ห้ามเก็บ secret ใน git, ห้าม disable type check / lint เพื่อให้ผ่าน
- ห้าม restart / แก้ config ของ MariaDB, FreeRADIUS, nginx และ certbot; คำสั่งที่ต้อง `sudo` ให้แสดงให้ผู้ใช้ดูและขออนุมัติก่อนรัน
- รัน service แบบ manual (uvicorn 8001 / vite 5174) หรือผ่าน `docker-compose.app.yml` (backend/frontend เท่านั้น) ก็ได้ — ห้ามสร้าง systemd unit หรือแก้ nginx **ของเครื่องจริง** ในเฟสนี้
- อธิบายและถามผู้ใช้เป็นภาษาไทย แต่โค้ด, comment, commit, และ log เป็นภาษาอังกฤษ
