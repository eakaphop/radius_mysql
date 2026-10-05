# Decisions Log

บันทึกการตัดสินใจที่ `CLAUDE.md` ไม่ได้ระบุไว้ชัดเจน พร้อมเหตุผล

## 2026-09-13 — เขียนโค้ดโดยไม่มีสิทธิ์เข้าเครื่องเป้าหมายจริง

เครื่อง dev ที่ใช้เขียนโค้ดนี้ (Windows, เข้าถึงผ่าน network share) ไม่มี Python, Node.js,
Docker หรือ ช่องทาง SSH เข้าเครื่อง Linux ที่รัน FreeRADIUS/MariaDB จริง จึง:

- ไม่สามารถรันคำสั่งสำรวจเครื่องในหัวข้อ 2 ของ `CLAUDE.md` ได้ — บันทึกเป็น TODO ไว้ใน
  `docs/environment.md` แทน ใช้ค่าที่ทราบอยู่แล้ว + placeholder
- ไม่สามารถรัน `pip install`, `npm install`, `pytest`, `vitest`, `alembic upgrade` เพื่อทดสอบ
  โค้ดที่เขียนได้จากเซสชันนี้ — ผู้ใช้ต้อง pull โค้ดไปรันบนเครื่องที่มี toolchain จริง
  (เครื่องเป้าหมาย หรือเครื่อง dev ที่มี Docker สำหรับ `docker-compose.dev.yml`) แล้วรัน
  test suite ก่อนเชื่อว่าใช้งานได้จริง
- เพิ่ม `docker-compose.dev.yml` สำหรับ dev/test นอกเครื่องเป้าหมาย ตามที่ `CLAUDE.md`
  หัวข้อ 10 ข้อ 1 อนุญาตไว้ ("dev นอกเครื่องใช้ docker-compose.dev.yml")

## 2026-09-13 — Phase 3: Users + Groups (เรื่องที่สเปกไม่ได้ระบุ)

- **แยก declarative base 2 ตัว**: ตาราง `app_*` ใช้ `Base` (Alembic จัดการ), ตาราง
  FreeRADIUS เดิม (`radcheck`, `radreply`, `radusergroup`, `radgroupcheck`,
  `radgroupreply`, `radacct`) ใช้ `FreeradiusBase` ที่ metadata **ไม่ถูกส่งให้ Alembic**
  — กัน `alembic revision --autogenerate` เผลอสร้าง migration แก้ตาราง FreeRADIUS
  (ข้อห้ามใน CLAUDE.md หัวข้อ 2/4.1)
- **ลำดับความสำคัญของ status**: `disabled` > `expired` > `active` — ถ้ามีทั้ง
  `Auth-Type := Reject` และ `Expiration` ที่เลยกำหนด จะรายงานเป็น `disabled`
- **ขอบเขตของ `PUT /users/{username}`**: แทนที่ `groups`, `expiration`,
  `reply_attributes` ทั้งชุด แต่ **ไม่แตะ** row รหัสผ่านและ row `Auth-Type := Reject`
  (มี endpoint `PATCH .../password` และ `PATCH .../status` แยกอยู่แล้ว) — กันการแก้
  ข้อมูลอื่นโดยไม่ตั้งใจ และ check attribute อื่นๆ (เช่น `Calling-Station-Id`) ยังไม่อยู่
  ในขอบเขต CRUD ของเฟสนี้ตามที่ body ใน CLAUDE.md หัวข้อ 5 ระบุไว้
- **`priority` ใน `radusergroup`**: กำหนดตามลำดับที่ส่งมาใน `groups[]` (1..n)
- **`sort` ของ `GET /users`**: รองรับ `username` และ `-username` เท่านั้น (ง่ายที่สุด
  ตามที่สเปกไม่ได้ระบุรายละเอียด) — ขยายทีหลังได้
- **`service_type` ของ user**: ดึงจาก prefix ของชื่อ group (`pppoe-*` / `hotspot-*`)
  เท่านั้นในเฟสนี้ ส่วนการดูจาก `radacct.servicetype`/`nasporttype` ของ session ล่าสุด
  (ตาม CLAUDE.md 6.1) เลื่อนไปทำในเฟส Sessions ที่ query `radacct` อยู่แล้ว — เลี่ยง
  query ตารางใหญ่ในหน้า list ผู้ใช้
- **`DELETE /groups/{groupname}`**: ลบเฉพาะ row ใน `radgroupcheck`/`radgroupreply`
  ไม่ลบ membership ใน `radusergroup` (FreeRADIUS ไม่มี FK ตรงนี้ และการถอด user
  ออกจาก group เงียบๆ เสี่ยงกว่าการปล่อย membership ที่ไม่ให้ attribute อะไรแล้ว)
- **"group มีอยู่จริง"** = มี row อย่างน้อยหนึ่งแถวใน `radgroupcheck`, `radgroupreply`
  หรือ `radusergroup` — group ที่มีแต่สมาชิก หรือมีแต่ reply attribute ก็ถือว่ามีอยู่

## 2026-09-14 — bcrypt/passlib incompatibility on first real run

รันบนเครื่องจริงครั้งแรกแล้วเจอ `AttributeError: module 'bcrypt' has no attribute
'__about__'` ตอนเรียก `python -m app.cli.create_admin` — `passlib` 1.7.4 (ยังไม่มี
release ใหม่กว่านี้ ณ ตอนเขียน) อ่านเลขเวอร์ชันผ่าน `bcrypt.__about__.__version__`
ซึ่ง `bcrypt` เอาออกตั้งแต่ 4.1.0 เป็นต้นไป แก้โดยล็อก `bcrypt<4.1` ใน
`backend/pyproject.toml` — ถ้า venv เดิมติดตั้ง bcrypt ใหม่ไปแล้วต้องรัน
`pip install -e ".[dev]"` ซ้ำ (หรือ `pip install "bcrypt<4.1" --force-reinstall`)
เพื่อดาวน์เกรด

## 2026-09-13 — Phase 4–7: NAS, Traffic Shaping, Accounting/Sessions, Dashboard, Audit, Settings

- **เพิ่มตาราง `app_profile_assignments`** (ไม่มีใน CLAUDE.md 4.2): บันทึกว่า profile ไหน
  ถูก apply กับ group/user ใด — จำเป็นสำหรับ `GET /shaping/profiles/{id}/targets`, การถาม
  "re-apply ไปยังทุก target" และ "effective profile" ใน UI เพราะเดาย้อนจากค่าใน
  `radreply`/`radgroupreply` ไม่ได้อย่างน่าเชื่อถือ (ผู้ใช้อาจแก้ค่ามือ) ลบ user/group จะลบ
  record นี้ด้วย
- **Group reply ใช้ operator `=` ไม่ใช่ `:=`**: FreeRADIUS อ่าน `radreply` (user) ก่อน
  `radgroupreply` ถ้า group เขียนด้วย `:=` จะ *ทับ* ค่าของ user ทำให้ "user override group"
  ตาม CLAUDE.md 6.1 ไม่เกิดขึ้นจริง จึงเขียน group ด้วย `=` (เพิ่มเฉพาะเมื่อยังไม่มี)
  ส่วน apply ระดับ user ยังใช้ `:=` ตามสเปก; `Simultaneous-Use` เป็น check attribute
  ใช้ `:=` ทั้งสองระดับ
- **`DELETE /shaping/profiles/{id}` ปฏิเสธ (409) ถ้ายังถูก apply อยู่** — ต้อง apply profile
  อื่นทับหรือแก้ attribute เองก่อน เพื่อไม่ให้ค่าใน DB ค้างโดยไม่รู้ที่มา
- **radclient ส่ง secret ผ่านไฟล์ชั่วคราว (`-S`, mode 0600) ไม่ใส่ใน argv** — argv อ่านได้
  จาก process list ของ user อื่นบนเครื่อง; ค่าทุก attribute ถูก quote/escape และปฏิเสธ
  ค่าที่มี line break เพื่อกัน attribute injection
- **`radpostauth` ไม่มีคอลัมน์ NAS** ใน schema มาตรฐาน FreeRADIUS 3.x (มีแค่ id, username,
  pass, reply, authdate) — หน้า Auth Log จึงไม่มี filter/คอลัมน์ NAS ตามที่ CLAUDE.md
  หัวข้อ 1 คาดไว้; คอลัมน์ `pass` **ไม่ถูก map** เพราะอาจมีรหัสผ่านที่ client ส่งมา
  เรียงลำดับด้วย `id` (ไม่มี index ที่ `authdate`)
- **Timezone**: ตาราง `app_*` เก็บ naive UTC, ตาราง FreeRADIUS เก็บเวลาเครื่อง server
  (MariaDB `NOW()`) — response ทั้งหมด serialize เป็น ISO-8601 พร้อม offset ผ่าน
  `utils/timezones.py` (`UtcDateTime` / `RadiusDateTime`) และค่า `Expiration` แปลงจาก
  input ของ browser เป็นเวลา server ก่อนเขียน
- **Dashboard traffic นับตามวันที่ session *เริ่ม*** (`acctstarttime`) ไม่แบ่ง session ที่
  ข้ามคืน — ง่ายที่สุดและ query ใช้ index ได้; `acctoutputoctets` = ดาวน์โหลดของ user
- **Accounting ถ้าไม่ระบุ `from` จะจำกัด 30 วันย้อนหลัง** เพื่อไม่ให้ scan `radacct` ทั้งตาราง;
  CSV stream ผ่าน session แยก (FastAPI ปิด dependency ก่อน body ของ StreamingResponse
  ถูกอ่าน) และ escape ค่าที่ขึ้นต้นด้วย `= + - @` กัน formula injection ใน spreadsheet
- **Session classifier** (`services/session_classifier.py`): PPPoE = `Framed-Protocol=PPP`
  หรือ `Service-Type=Framed-User` หรือ `NAS-Port-Type=Virtual`; Hotspot =
  `Service-Type=Login-User` หรือ `NAS-Port-Type=Wireless-802.11`; `Ethernet` เดี่ยวๆ
  ถือว่า unknown — **ต้องตรวจกับ radacct จริง** (TODO ใน environment.md)
- **`GET /sessions/capabilities`** เพิ่มเพื่อให้ UI ซ่อนปุ่ม Disconnect/CoA ตาม
  `ENABLE_POD`/`ENABLE_COA` โดยไม่ต้องยิงแล้วรอ 501
- **เปลี่ยนรหัสผ่าน admin (`PATCH /auth/me/password`)** revoke refresh token อื่นทั้งหมด
  ยกเว้น session ปัจจุบัน
- **ภาษาที่เลือกเก็บใน `localStorage`** (key `radius-manager.language`) — เป็น UI preference
  ไม่ใช่ token จึงไม่ขัดกับข้อห้ามใน CLAUDE.md หัวข้อ 6
- **Frontend ไม่มี shadcn จริง**: เครื่องที่เขียนไม่มี Node จึงรัน `npx shadcn init` ไม่ได้
  ใช้ primitives ที่เขียนเองด้วย Tailwind ใน `src/components/ui/primitives.tsx` แทน
  (แทนที่ทีละไฟล์ได้ทีหลัง)
- **กราฟ Dashboard ใช้ palette ที่ validate แล้ว** (`src/lib/chartPalette.ts`): ดาวน์โหลด/
  อัปโหลด = categorical slot 1/2, accept/reject = status good/critical; แกนเดียวต่อกราฟ
  และมี legend + label เสมอ (ไม่ใช้สีอย่างเดียวสื่อความหมาย)

## 2026-09-13 — รูปแบบ transaction ใน service layer

CLAUDE.md หัวข้อ 5 เขียนว่า "ทุก write operation ต้อง `async with session.begin()`"
แต่ในทางปฏิบัติกับ SQLAlchemy 2.x async + session ต่อ request (FastAPI dependency
`get_db` ให้ session เดียวใช้ตลอด request) ถ้ามีการอ่านข้อมูล (เช่น query หา user)
เกิดขึ้นก่อนในเซสชันเดียวกัน (autobegin transaction เริ่มไปแล้ว) แล้วค่อยเรียก
`async with session.begin()` ซ้ำ จะได้ error
`InvalidRequestError: A transaction is already begun on this Session`

ทางออกที่ใช้ (ดู `backend/app/services/auth_service.py`): ไม่เรียก `session.begin()`
ตรงๆ ในฟังก์ชัน service แต่ปล่อยให้ autobegin ทำงาน แล้วเรียก `await db.commit()`
ครั้งเดียวหลังเขียนข้อมูลครบ (รวม audit log) ในฟังก์ชันเดียวกัน —ยังคงเป็น
atomic transaction เดียวตามเจตนาของสเปก เพียงไม่ได้ใช้ syntax `async with` ตรงตัว
**ให้ service ในเฟสถัดไปทั้งหมดใช้ pattern เดียวกันนี้** (เขียนข้อมูล + audit log
แล้ว commit ครั้งเดียวท้ายฟังก์ชัน) เพื่อความสม่ำเสมอ

## 2026-09-13 — ลำดับการทำงาน

ทำทีละ phase ตามหัวข้อ 10 แล้วหยุดให้ผู้ใช้ตรวจก่อนไปขั้นถัดไป (คำสั่งผู้ใช้ในเซสชันนี้)
เริ่มจาก Scaffold (phase 1) ก่อน

## 2026-09-16 — UniFi traffic shaping ผ่าน Filter-Id

UniFi Network Controller ไม่มี RADIUS VSA สำหรับส่งตัวเลข rate limit ตรงๆ แบบ
MikroTik (`Mikrotik-Rate-Limit`) — กลไกที่ Ubiquiti รองรับอย่างเป็นทางการคือส่ง
`Filter-Id` ที่มีค่าตรงกับชื่อ **Bandwidth Profile** ที่ผู้ดูแลต้องสร้างไว้ล่วงหน้า
ในหน้า UniFi Network Controller เอง (Settings > Profiles > Bandwidth Profiles)
แล้วตัว controller จะไปค้นหาค่า limit จากโปรไฟล์นั้นเอง — ระบบนี้จึงทำหน้าที่แค่
"อ้างอิงชื่อ" ผ่าน RADIUS ไม่ได้ควบคุมตัวเลขความเร็วแทน UniFi ได้จริง (ต่างจาก
MikroTik ที่ส่งตัวเลขไปตรงๆ)

การใช้งาน: เพิ่ม field `unifi_filter_id` ใน Bandwidth Profile (migration 0003)
เมื่อตั้งค่านี้ `build_attributes()` จะเพิ่ม reply attribute `Filter-Id := <ชื่อ>`
เข้าไปด้วย (ใช้ operator `:=` เหมือน attribute อื่นตอน apply กับ user, และ `=`
ตอน apply กับ group ตาม pattern เดิมที่ `GROUP_REPLY_OPERATOR` กำหนดไว้ใน
`shaping_service.py`) — profile หนึ่งตัวจึงตั้งค่าได้ทั้ง MikroTik และ UniFi
พร้อมกันได้ถ้าต้องการ (ไม่ได้ผูกกับ `service_type` ซึ่งหมายถึง pppoe/hotspot
ของ MikroTik เท่านั้น)

**สิ่งที่ผู้ใช้ต้องทำเองบน UniFi Controller** (ระบบนี้ทำแทนไม่ได้): สร้าง
Bandwidth Profile ที่มีชื่อ "ตรงตัวอักษรทุกตัว" กับค่าที่กรอกในฟอร์มนี้ก่อน
ไม่เช่นนั้น `Filter-Id` จะถูกส่งไปแต่ไม่มีผลใดๆ (ไม่มี error ให้เห็น เพราะ RADIUS
ยังตอบ Accept ตามปกติ)

## 2026-09-17 — Dark mode + ภาษาเริ่มต้นเปลี่ยนเป็นอังกฤษ

**Dark mode**: เพิ่ม `ThemeProvider` (`frontend/src/app/ThemeProvider.tsx`) เก็บค่าที่
เลือกใน `localStorage` key `radius-manager.theme` (UI preference ล้วนๆ ไม่ใช่ token
จึงไม่ขัด CLAUDE.md หัวข้อ 6) ค่าเริ่มต้นตาม `prefers-color-scheme` ของเครื่อง
แล้วยังคง sync ตาม OS ต่อไปจนกว่าผู้ใช้จะกดสลับเองครั้งแรก (หลังจากนั้นค่าที่เลือก
เองชนะเสมอ) ใช้ Tailwind `darkMode: "class"` เดิมที่ตั้งไว้แล้ว โดย toggle class
`dark` บน `<html>` — มี inline script เล็กๆ ใน `index.html` ตั้ง class นี้ตั้งแต่
ก่อน paint เพื่อกัน flash แสงสว่างตอนโหลดหน้าตอน theme เป็น dark (ต้อง sync
storage key กับ `ThemeProvider.tsx` เอง ถ้าเปลี่ยนชื่อ key ต้องแก้ทั้งสองที่)

Token สี (`src/index.css`) เพิ่ม `.dark { ... }` ทับค่า `:root` เดิม (ไม่ใช่ invert
อัตโนมัติ — ไล่ค่าทีละตัวให้ contrast อ่านง่ายบนพื้นเข้ม) ส่วน badge/alert tone
ที่ hardcode สี Tailwind ตรงๆ (เช่น `bg-green-100 text-green-800`) ใน
`components/ui/primitives.tsx` เพิ่ม `dark:` variant คู่กันทุกตัว

กราฟ Dashboard (`TrafficChart`, `AuthStatsChart`) **ทำตามกฎ dataviz skill ข้อ 6
ตรงตัว**: "dark mode is selected — its own steps from the same ramps, validated
against the dark surface, not an automatic flip" — ค่าสี dark ทั้งหมดใน
`src/lib/chartPalette.ts` (`chartColors("dark")`) ก็อปมาจาก
`references/palette.md` ของ dataviz skill ตรงๆ ไม่ได้คิดเอง: categorical slot 1/2
dark step (`#3987e5`, `#d95926`), chart chrome dark (surface `#1a1a19`, gridline
`#2c2c2a`, axis `#383835`, primary ink `#ffffff`, muted ink `#898781` เท่าเดิมทั้ง
สองโหมด) และ status good/critical **ใช้ hex เดิมทั้งสองโหมด** (status palette
ถูก fix ไว้ ไม่ theme ตามข้อกำหนดของ skill) ตัวเลข validate (adjacent CVD ΔE 9.1
light / 8.4 dark, normal-vision ΔE 19.6 light / 19.3 dark) มาจาก reference palette
ที่ validate ไว้แล้วในสเปกของ skill เอง (ไม่ใช่ palette ที่ custom เอง จึงไม่ต้องรัน
validator ซ้ำ)

**ภาษาเริ่มต้น**: ผู้ใช้ขอให้เมนูเป็นอังกฤษทั้งหมด — เปลี่ยน `fallbackLng` และค่า
เริ่มต้นตอนไม่มี `localStorage` key `radius-manager.language` จาก `"th"` เป็น
`"en"` ใน `frontend/src/app/i18n.ts` (และ `index.html` lang attribute) **หมายเหตุ**:
browser ที่เคยตั้งค่า "th" ไว้ใน localStorage จะยังเห็นภาษาไทยต่อไปจนกว่าจะไปเลือก
English เองที่หน้า Settings (ค่าที่ผู้ใช้เคยเลือกเองชนะค่า default เสมอ)

## 2026-10-05 — แยก "admin เข้าเว็บ" ออกจาก Online Sessions ของลูกค้าจริง

ผู้ใช้แจ้งว่าหน้า Online Sessions (`radacct` ที่ `acctstoptime IS NULL`) นับ
session ของ admin เองรวมด้วย เพราะ admin ใช้ RADIUS account เดียวกับที่ใช้ต่อเน็ต
เข้าเว็บแอปนี้ (เช่น PPPoE account ของ office) — ไม่ใช่ bug ของ query แต่เป็น
account จริงที่ authenticate ผ่าน FreeRADIUS เหมือน user ทั่วไป ระบบจึงแยกไม่ออก
เองว่า account ไหนคือ "ลูกค้า" กับ "infrastructure"

แก้ด้วย config ใหม่ `ONLINE_SESSIONS_EXCLUDE_USERNAMES` (comma-separated, ใน
`backend/.env`) กรอง `RadAcct.username NOT IN (...)` ใน
`sessions_service.list_online_sessions` — เลือกใช้ env var (เหมือน
`ENABLE_POD`/`ENABLE_COA`) แทนการเพิ่มตาราง/หน้า settings ใหม่ เพราะรายชื่อ
account แบบนี้เปลี่ยนไม่บ่อยและมีไม่กี่ตัว ถ้าในอนาคตต้องแก้บ่อยจากหน้าเว็บโดยตรง
ค่อยย้ายไปเป็น app setting ทีหลัง **ขอบเขต**: กรองเฉพาะ `/sessions/online` —
ไม่แตะ `/accounting` (ประวัติ) หรือตัวเลข Dashboard (`online_users`/
`online_sessions`) เพราะผู้ใช้ไม่ได้ขอให้ตัวเลขสรุปเปลี่ยน ถ้าต้องการให้ตัดออกจาก
จุดอื่นด้วยค่อยขยายทีหลัง

## 2026-10-05 — Docker image สำหรับ backend/frontend เท่านั้น (สวนทาง CLAUDE.md เดิม)

ผู้ใช้ขอให้สร้าง Docker สำหรับ backend/frontend โดยเฉพาะ ทั้งที่ CLAUDE.md หัวข้อ
7/10 เดิมระบุว่า Docker/production build ยังไม่อยู่ในขอบเขต (เฟสถัดไป) — ผู้ใช้
ยืนยันให้ทำและอัปเดต CLAUDE.md ให้ตรงกับการตัดสินใจนี้ด้วย (แก้ไขแล้วในหัวข้อ 7/10/11)

- **ไม่มี service MariaDB/FreeRADIUS/nginx ใน compose นี้** — ยังใช้ของเดิมบนเครื่อง
  จริงตาม "Infrastructure" เดิมทุกประการ ไม่ขัดกับกฎ "ห้ามติดตั้งซ้ำ"
- **`network_mode: host`** แทน bridge network เพราะ `docs/environment.md` ระบุว่า
  MariaDB bind `localhost:3306` เท่านั้น และ `radclient` (PoD/CoA) ต้องยิงไปหา
  MikroTik บน LAN ตรงๆ — bridge network ต้องเพิ่ม gateway/port-forward config
  ทั้งสองทาง ส่วน host network ใช้ `DB_HOST=localhost`/`RADCLIENT_PATH` เดิมได้โดย
  ไม่ต้องแก้ค่าใน `.env` เลย (ใช้ได้เฉพาะบน Linux host จริง ไม่ใช่ Docker Desktop)
- **`VITE_API_BASE_URL` เป็น build arg ไม่ใช่ runtime env** เพราะ Vite inline
  ค่า `VITE_*` ตอน build เท่านั้น (ข้อจำกัดของ Vite เอง ไม่ใช่การตัดสินใจ) — ถ้า
  deploy ไปคนละเครื่อง/IP ต้อง build image ใหม่ทุกครั้งที่ IP เปลี่ยน **(แก้แล้วใน
  decision ถัดไปด้านล่าง — ค่า default เปลี่ยนเป็น relative path ที่ย้ายปัญหานี้ออกไป
  สำหรับ setup ทั่วไป)**
- **frontend ใช้ nginx:alpine serve static ในคอนเทนเนอร์ตัวเอง** — คนละตัวกับ
  nginx ของเครื่องจริงที่ CLAUDE.md ห้ามแตะ (`frontend/nginx.conf` เป็น config
  ของ container นี้เท่านั้น ไม่เกี่ยวกับ `/etc/nginx` บนเครื่องจริง)
- `docker-compose.app.yml` แยกจาก `docker-compose.dev.yml` เดิม (ไฟล์นั้นมีไว้รัน
  MariaDB local สำหรับ dev นอกเครื่องเป้าหมายเท่านั้น คนละวัตถุประสงค์กัน)

## 2026-10-05 — HTTPS/Let's Encrypt ผ่าน container `caddy` แยก ไม่แตะ nginx/certbot เครื่องจริง

ผู้ใช้ deploy ด้วย Docker สำเร็จแล้วขอเพิ่ม HTTPS + Let's Encrypt ต่อ แต่
CLAUDE.md หัวข้อ "Infrastructure" ระบุชัดว่า nginx และ certbot ของเครื่องจริง
**มี site อื่นใช้งานอยู่แล้วและมี cert อยู่แล้ว ห้ามแตะ** — ถามผู้ใช้แล้วเลือกแนวทาง
"ทำ HTTPS แยกในคอนเทนเนอร์ของตัวเอง ไม่แตะ nginx/certbot เครื่องจริงเลย"

**ปัญหาและทางแก้ที่เลือก:**

1. **Port 80/443 ถูก nginx เดิมยึดอยู่แล้ว** — ACME challenge แบบ HTTP-01/
   TLS-ALPN-01 ผูกกับ port 80/443 ตายตัวตาม spec เอง ไม่สามารถกำหนด port อื่น
   ได้ ดังนั้นถ้าจะไม่แตะ nginx เดิมเลย เหลือทางเดียวคือ **DNS-01 challenge**
   (proof ความเป็นเจ้าของ domain ผ่าน DNS TXT record แทนการเปิด port) — ผู้ใช้
   ใช้ Cloudflare เป็น DNS ของ domain นี้อยู่แล้ว จึง build Caddy custom ผ่าน
   `xcaddy` ใส่ module `github.com/caddy-dns/cloudflare` (`caddy/Dockerfile`)
2. **ไม่มี port 443 ให้ bind** (เครื่องจริงใช้อยู่) — ผู้ใช้ยอมรับให้ใช้ port อื่นแทน
   เช่น `:8443` (`caddy/Caddyfile` อ่านจาก env `HTTPS_PORT`) เข้าเว็บจะได้เป็น
   `https://<SITE_DOMAIN>:8443` ไม่ใช่ port 443 มาตรฐาน — DNS-01 ไม่สนใจว่า user
   เข้าทาง port ไหนอยู่แล้ว (challenge ไม่ผ่าน port เลย) จึงไม่ติดขัดเรื่องนี้
3. **Mixed content**: หน้าเว็บโหลดผ่าน HTTPS แต่เดิม frontend build เรียก API
   เป็น absolute URL แบบ `http://<ip>:8001/...` ตรงๆ — browser จะ block request
   แบบนี้ทันที (active mixed content) ถ้าไม่แก้ login ผ่าน HTTPS จะไม่มีทางทำงาน
   ได้เลย แก้โดยเปลี่ยนสถาปัตยกรรม: **`frontend/nginx.conf` เพิ่ม `location /api/`
   proxy_pass ไปที่ `127.0.0.1:8001`** (ใช้ได้เพราะ `network_mode: host` อยู่แล้ว)
   และเปลี่ยนค่า default ของ `VITE_API_BASE_URL` ใน `frontend/Dockerfile` จาก
   absolute URL เป็น **relative path `/api/v1`** ผลคือ frontend image เดียวกัน
   เรียก backend แบบ same-origin เสมอ ไม่ว่าจะเข้าทาง port 5174 ตรงๆ หรือผ่าน
   Caddy HTTPS — ได้ผลพลอยได้คือ**เลิกต้องพึ่ง CORS_ORIGINS เป๊ะๆ สำหรับทางเข้านี้
   ไปด้วย** (same-origin ไม่ติด CORS) ซึ่งแก้ปัญหา CORS ที่ผู้ใช้เจอซ้ำๆ ตอน deploy
   Docker รอบก่อนหน้าไปในตัว — เป็นการเปลี่ยน default ของ image ที่ deploy ไปแล้ว
   รอบก่อน **ต้อง rebuild frontend ใหม่ถึงจะได้พฤติกรรมนี้**
4. **Caddy ใช้ `network_mode: host` เหมือน backend/frontend** เพื่อ reach
   `127.0.0.1:5174` ได้ตรงๆ และ bind `HTTPS_PORT` บนเครื่องจริงได้ตรงๆ โดยไม่ต้อง
   publish port เพิ่ม — เหตุผลเดียวกับที่เลือก host network ให้ backend/frontend
   ใน decision ก่อนหน้า
5. **`COOKIE_SECURE` setting ใหม่** (`backend/app/core/config.py`,
   `backend/app/api/v1/auth.py`) — refresh token cookie เดิม hardcode
   `secure=False` เพราะตอนนั้นมีแต่ HTTP ตอนนี้มี HTTPS จริงแล้วควรเปิด `Secure`
   flag ได้ แต่เปิด conditionally ผ่าน env แทนการ hardcode `True` เพราะทางเข้า
   HTTP ตรงๆ (port 5174) ยังใช้งานคู่ขนานอยู่ และ cookie ที่มี flag `Secure` จะไม่
   ถูกส่งกลับถ้าเข้าทาง HTTP — สองทางเข้าใช้ค่านี้ร่วมกันไม่ได้ ถ้าเลือกใช้ HTTPS
   ทางเดียวค่อยตั้ง `COOKIE_SECURE=true`
6. **`docker-compose.caddy.yml` แยกไฟล์** ไม่รวมเข้า `docker-compose.app.yml`
   เพราะ Cloudflare-specific (ต้องมี `CF_API_TOKEN`) ไม่ใช่ทุก deployment จะมี —
   รันคู่กันด้วย `docker compose -f docker-compose.app.yml -f docker-compose.caddy.yml up -d`
7. **ขอบเขต**: แก้ `CLAUDE.md` หัวข้อ 7/8/10 ให้ตรงกับการตัดสินใจนี้ (nginx/certbot
   เครื่องจริงยังห้ามแตะเหมือนเดิม — เปลี่ยนแค่ว่า "HTTPS ยังไม่ทำ" เป็น "ทำแล้วผ่าน
   container แยก")

## 2026-10-06 — ถอด Caddy/HTTPS ออก กลับไปใช้ HTTP อย่างเดียวตามที่ผู้ใช้ขอ

Caddy container ขึ้นแล้ว crash-loop (`API token 'change-me' appears invalid`
— `caddy/.env` ยังเป็นค่า placeholder จาก `.env.example` ไม่เคยแก้เป็น
Cloudflare token จริง) ผู้ใช้ตัดสินใจไม่สู้กับขั้นตอน Cloudflare token /
DNS-01 ต่อ ขอให้เอา Caddy ออกจากโปรเจกต์ทั้งหมดแล้วใช้ HTTP อย่างเดียวพอ

**ลบ**: `caddy/` ทั้งโฟลเดอร์ (`Dockerfile`, `Caddyfile`, `.env.example`),
`docker-compose.caddy.yml`, การอ้างอิงถึง Caddy/HTTPS ใน `README.md` และ
`CLAUDE.md` (คืนข้อความหัวข้อ 7/8/10 กลับไปใกล้เคียงก่อนทำ Caddy — HTTPS/nginx
reverse proxy ของเครื่องจริงยังเป็น "เฟสถัดไป" เหมือนเดิม), `COOKIE_SECURE`
setting (`backend/app/core/config.py`, `backend/app/api/v1/auth.py` —
cookie กลับไป hardcode `secure=False` เหมือนก่อนทำ Caddy เพราะไม่มี HTTPS
deployment path เหลืออยู่แล้วที่จะใช้ค่านี้)

**ไม่ลบ**: การแก้ `frontend/nginx.conf` ให้ proxy `/api/` ไปที่ backend เอง
และเปลี่ยน default `VITE_API_BASE_URL` ใน `frontend/Dockerfile` เป็น relative
path `/api/v1` — สองอย่างนี้ไม่ได้ผูกกับ Caddy โดยตรง แก้ปัญหาจริงที่เคยเจอตอน
deploy HTTP ล้วนๆ ด้วยเช่นกัน (build-arg ผิด IP ทำให้ login ไม่ได้, CORS ปวดหัว
ซ้ำๆ) ยังมีประโยชน์อยู่แม้ไม่มี Caddy แล้ว
