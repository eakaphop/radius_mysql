# Environment Survey

บันทึกค่าที่พบจากเครื่องเป้าหมายจริงที่รัน FreeRADIUS + MariaDB
(ดูขั้นตอนสำรวจใน `CLAUDE.md` หัวข้อ 2)

> **หมายเหตุ**: การเขียนโค้ดครั้งนี้ทำจากเครื่อง dev (Windows) ที่เข้าถึงโค้ดผ่าน
> network share เท่านั้น **ไม่มีช่องทางรันคำสั่งสำรวจ (`grep`, `mysql`, `ss`) บนเครื่อง
> Linux เป้าหมายจริงได้** ค่าด้านล่างเป็นค่าที่ทราบจาก `CLAUDE.md` เดิมบวก placeholder
> — **ผู้ใช้ต้องรันคำสั่งในหัวข้อ 2 ของ `CLAUDE.md` บนเครื่องจริงแล้วอัปเดตไฟล์นี้เอง
> ก่อน deploy ใช้งานจริง**

## MariaDB / FreeRADIUS SQL

| รายการ | ค่า | สถานะ |
|---|---|---|
| MariaDB server | `localhost:3306` | ยืนยันแล้ว (จาก `mods-available/sql`) |
| Database | `radius` | ยืนยันแล้ว |
| DB user ที่ FreeRADIUS ใช้ | `radius` | ยืนยันแล้ว (รหัสผ่านอยู่บนเครื่องจริงเท่านั้น ห้ามบันทึกที่นี่) |
| DB user ของ web app | `radius` (ใช้ user เดิมของ FreeRADIUS ตามที่ผู้ใช้เลือก — รหัสผ่านอยู่ใน `backend/.env` บนเครื่องเท่านั้น) | ยืนยันแล้ว 2026-09-13 — ไม่ต้องรัน `scripts/create-db-user.sql` (เก็บไว้เผื่ออยากแยก user ทีหลัง) |
| สิทธิ์ของ user `radius` บน DB | **ไม่ทราบ** — Alembic ต้องมี `CREATE/ALTER/DROP/INDEX` บน `radius.*` เพื่อสร้างตาราง `app_*` + `alembic_version` | ⬜ TODO: รัน `SHOW GRANTS FOR 'radius'@'localhost'` ถ้ามีแค่ SELECT/INSERT/UPDATE/DELETE ให้รัน `alembic upgrade head` ครั้งแรกด้วย user ที่มีสิทธิ์ (root) แล้ว grant เพิ่มตาม `scripts/create-db-user.sql` (แก้ชื่อ user เป็น `radius`) |
| FreeRADIUS version | **ไม่ทราบ** | ⬜ TODO: รัน `freeradius -v` หรือ `radiusd -v` |
| FreeRADIUS config path | **ไม่ทราบ** — `/etc/freeradius/3.0` (Debian/Ubuntu) หรือ `/etc/raddb` (RHEL/Rocky) | ⬜ TODO: ยืนยันว่าเป็น path ไหน |
| IP ของเครื่องเป้าหมาย (LAN) | **ไม่ทราบ** | ⬜ TODO: ใช้เติม `CORS_ORIGINS`, `VITE_API_BASE_URL` |
| Port 8001 / 5174 ว่างหรือไม่ | **ไม่ทราบ** | ⬜ TODO: รัน `ss -lntp \| grep -E ':(8001\|5174)'` |
| คอลัมน์ `groupname` ใน `radacct` | **ไม่มี** — ยืนยันแล้ว 2026-10-05 จาก error จริง `Unknown column 'radacct.groupname' in 'SELECT'` ตอนเปิดหน้า Accounting/Online Sessions | ยืนยันแล้ว — เอา `groupname` ออกจาก `RadAcct` model แล้ว (ดู `backend/app/db/models/radius.py`) |

### ⚠️ ต้องตรวจสอบก่อนใช้งาน
พบใน `CLAUDE.md` ว่าไฟล์ `mods-available/sql` มีบรรทัด
`radius_db = "(DESCRIPTION=...` (รูปแบบ Oracle) ที่ดูเหมือนไม่ได้ comment `#` ไว้
— **ห้ามแก้เอง** ต้องแจ้งผู้ใช้และรอคำยืนยันก่อน (อาจเป็น dialect อื่นที่ค้างอยู่ในไฟล์ config
โดยไม่ได้ใช้งานจริง หรืออาจทำให้ FreeRADIUS โหลด SQL module ผิด instance)

## MikroTik / CoA (ต้องทดสอบกับอุปกรณ์จริง)

| รายการ | ค่า | สถานะ |
|---|---|---|
| RouterOS version ของ MikroTik ที่ใช้ | **ไม่ทราบ** | ⬜ TODO |
| `/radius incoming set accept=yes port=3799` ตั้งแล้วหรือยัง | **ไม่ทราบ** | ⬜ TODO (ต้องตรงกับ secret ในตาราง `nas`) |
| ผลทดสอบ Disconnect (PoD) กับ PPPoE / Hotspot | **ยังไม่ทดสอบ** | ⬜ TODO บันทึก ACK/NAK + Error-Cause ที่ได้ |
| ผลทดสอบ CoA เปลี่ยน `Mikrotik-Rate-Limit` กับ session ที่ online | **ยังไม่ทดสอบ** | ⬜ TODO |
| `radclient` อยู่ที่ `/usr/bin/radclient` หรือไม่ (`which radclient`) | **ไม่ทราบ** | ⬜ TODO ใส่ใน `RADCLIENT_PATH` |
| ค่า `nasporttype` / `servicetype` / `framedprotocol` จริงใน `radacct` ของ PPPoE และ Hotspot | **ไม่ทราบ** | ⬜ TODO ใช้ยืนยันกฎใน `services/session_classifier.py` — รัน `SELECT nasporttype, servicetype, framedprotocol, COUNT(*) FROM radacct GROUP BY 1,2,3` |
| Timezone ของ MariaDB (`SELECT @@system_time_zone, @@time_zone`) | **ไม่ทราบ** | ⬜ TODO — backend ถือว่าเวลาใน `radacct`/`radpostauth` เป็นเวลาเครื่อง server |

## วิธีอัปเดตไฟล์นี้

รันบนเครื่องเป้าหมายจริงแล้ววางผลลัพธ์ที่ TODO ด้านบน:

```bash
grep -E "^\s*(server|port|login|password|radius_db|dialect)" /etc/freeradius/3.0/mods-available/sql
freeradius -v || radiusd -v
mysql -u root -p -e "SHOW DATABASES; USE radius; SHOW TABLES; SHOW CREATE TABLE radcheck\G"
ss -lntp | grep -E ':(8001|5174)'
ip -4 addr show | grep inet
```

**ห้ามคัดลอกรหัสผ่านจริงลงไฟล์นี้หรือไฟล์ใดใน repo** — ใส่ใน `.env` บนเครื่องเท่านั้น
(`.env` ต้องอยู่ใน `.gitignore`)

## Dev นอกเครื่องเป้าหมาย (สถานการณ์ปัจจุบัน)

เนื่องจากเขียนโค้ดจากเครื่องที่เข้าไม่ถึง MariaDB/FreeRADIUS จริง ให้ใช้
`docker-compose.dev.yml` (ที่ root) รัน MariaDB local สำหรับ dev/test แทน
โดย import schema จาก `docs/freeradius-schema.sql` เพื่อให้ตารางตรงกับของจริง
ห้ามใช้ SQLite เพราะ SQL dialect ต่างจาก MariaDB
