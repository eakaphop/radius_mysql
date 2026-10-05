# API Summary

Base path: `/api/v1`. ทุก endpoint ต้องส่ง `Authorization: Bearer <access_token>`
ยกเว้น `POST /auth/login`, `POST /auth/refresh` และ `GET /health` (อยู่นอก `/api/v1`)

Endpoint ที่แก้ไขข้อมูล (POST/PUT/PATCH/DELETE) ต้องมี role `admin`; role `viewer` อ่านได้อย่างเดียว

Swagger UI ฉบับเต็ม (สร้างจาก OpenAPI จริง): `http://<host>:8001/docs`
— ไฟล์นี้เป็นสรุปที่เขียนด้วยมือให้ตรงกับ router ใน `backend/app/api/v1/` ใช้อ่านคร่าวๆ
ถ้าไม่ตรงกันให้ยึด Swagger

## รูปแบบ response

```json
// list
{ "items": [...], "total": 123, "page": 1, "page_size": 25 }

// error (ทุก endpoint รวม 422 validation)
{ "detail": "ข้อความ", "code": "USER_NOT_FOUND" }
```

`page_size` สูงสุด 200 — วันเวลาใน response เป็น ISO-8601 พร้อม offset เสมอ
(ตาราง `app_*` เป็น UTC, ตาราง FreeRADIUS เป็นเวลาเครื่อง server) ให้ browser แปลงเป็น
timezone ของตัวเอง

## Auth
| Method | Path | หมายเหตุ |
|---|---|---|
| POST | `/auth/login` | rate limit 5 ครั้ง/นาที/IP → `{access_token, refresh_token, admin}` + cookie `refresh_token` (httpOnly, path `/api/v1/auth`) |
| POST | `/auth/refresh` | อ่าน refresh token จาก cookie (หรือ body `{refresh_token}` สำหรับ dev) แล้ว rotate |
| POST | `/auth/logout` | revoke refresh token + ลบ cookie |
| GET | `/auth/me` | |
| PATCH | `/auth/me/password` | `{current_password, new_password}` — revoke session อื่นทั้งหมดยกเว้นตัวปัจจุบัน |

## Users (radcheck + radreply + radusergroup)
| Method | Path | หมายเหตุ |
|---|---|---|
| GET | `/users?search=&group=&status=active\|disabled\|expired&page=&page_size=&sort=username\|-username` | |
| GET | `/users/{username}` | `has_password` แทนค่ารหัสผ่านจริง |
| POST | `/users` | `{username, password, groups[], expiration?, reply_attributes[]?}` |
| PUT | `/users/{username}` | แทนที่ `groups`, `expiration`, `reply_attributes` ทั้งชุด (ไม่แตะรหัสผ่าน/สถานะ) |
| PATCH | `/users/{username}/password` | `{password}` |
| PATCH | `/users/{username}/status` | `{enabled}` — ปิด = เพิ่ม `Auth-Type := Reject` |
| DELETE | `/users/{username}` | ลบ radcheck/radreply/radusergroup (ไม่ลบ radacct/radpostauth) |
| GET | `/users/{username}/sessions` | radacct ของ user (paginate) |

## Groups (radgroupcheck + radgroupreply)
| Method | Path | หมายเหตุ |
|---|---|---|
| GET | `/groups?search=&page=&page_size=` | รวมชื่อ group จากทั้ง 3 ตาราง |
| GET | `/groups/{groupname}` | |
| POST | `/groups` | `{groupname, check_attributes[], reply_attributes[]}` |
| PUT | `/groups/{groupname}` | แทนที่ attribute ทั้งชุด |
| DELETE | `/groups/{groupname}` | ลบ attribute ไม่ลบ membership |
| GET | `/groups/{groupname}/members` | |

## NAS
| Method | Path | หมายเหตุ |
|---|---|---|
| GET | `/nas?search=&page=&page_size=` | secret ถูก mask เป็น `***` |
| GET | `/nas/{id}?reveal=true` | `reveal` ต้อง role `admin` |
| POST | `/nas` | response มี `"warning": "FreeRADIUS reload required"` |
| PUT | `/nas/{id}` | มี warning เช่นกัน |
| DELETE | `/nas/{id}` | ตอบ `{warning}` |

## Traffic Shaping (MikroTik + UniFi)
| Method | Path | หมายเหตุ |
|---|---|---|
| GET | `/shaping/profiles?search=&page=&page_size=` | |
| POST | `/shaping/profiles` | body = ฟิลด์ profile (validate ตามกฎ 6.1); `unifi_filter_id` ถ้าตั้งไว้จะถูกส่งเป็น `Filter-Id` — ต้องสร้าง Bandwidth Profile ชื่อตรงกันในหน้า UniFi Controller เองก่อน (ดู docs/decisions.md 2026-09-16) |
| GET/PUT/DELETE | `/shaping/profiles/{id}` | DELETE ตอบ 409 `PROFILE_IN_USE` ถ้ายังมีคนใช้ |
| POST | `/shaping/preview` | ฟิลด์ profile → `{attributes, check_attributes, rate_limit_string}` ไม่บันทึก |
| POST | `/shaping/parse` | `{rate_limit}` → แยกเป็นฟิลด์ (ใช้ import ค่าเดิมจาก DB) |
| POST | `/shaping/profiles/{id}/apply` | `{target: "group"\|"user", name}` — ลบ shaping attribute เดิมแล้วเขียนใหม่ใน transaction เดียว; 409 `PROFILE_SERVICE_MISMATCH` ถ้า service ไม่ตรง |
| POST | `/shaping/profiles/{id}/reapply` | re-apply ไปยังทุก target ที่บันทึกไว้ (UI ถามก่อนเสมอ) |
| GET | `/shaping/profiles/{id}/targets` | group/user ที่ใช้ profile นี้ |
| GET | `/shaping/users/{username}/effective` | effective profile ของ user (user override group) + warning ถ้า group shaping ซ้อนกัน |

## Accounting (radacct)
| Method | Path | หมายเหตุ |
|---|---|---|
| GET | `/accounting?username=&nasipaddress=&from=&to=&page=&page_size=` | ถ้าไม่ส่ง `from` จะดูย้อนหลัง 30 วัน |
| GET | `/accounting/export?...` | CSV stream (filter เดียวกัน) |
| GET | `/accounting/{radacctid}` | |

## Sessions
| Method | Path | หมายเหตุ |
|---|---|---|
| GET | `/sessions/capabilities` | `{pod_enabled, coa_enabled}` ให้ UI ซ่อนปุ่ม |
| GET | `/sessions/online?service=all\|pppoe\|hotspot&page=&page_size=` | `acctstoptime IS NULL` แยกด้วย `services/session_classifier.py` |
| POST | `/sessions/{radacctid}/disconnect` | ต้อง `ENABLE_POD=true` ไม่งั้น 501 `POD_DISABLED` |
| POST | `/sessions/{radacctid}/coa` | `{profile_id}` หรือ `{rate_limit}`; ต้อง `ENABLE_COA=true` ไม่งั้น 501 `COA_DISABLED` |

ผลลัพธ์ PoD/CoA: `{success, response: "CoA-ACK"\|"CoA-NAK"\|..., error_cause, detail}`
และถูกบันทึกลง `app_audit_log` ทุกครั้ง

## Post-auth log
| Method | Path |
|---|---|
| GET | `/postauth?username=&reply=Access-Accept\|Access-Reject&from=&to=&page=&page_size=` |

## Dashboard
| Method | Path |
|---|---|
| GET | `/dashboard/summary` |
| GET | `/dashboard/traffic?days=7` |
| GET | `/dashboard/auth-stats?hours=24` |

## Audit
| Method | Path |
|---|---|
| GET | `/audit?admin=&resource_type=&from=&to=&page=&page_size=` |

`resource_type` ที่ใช้อยู่: `auth`, `admin_user`, `radius_user`, `radius_group`, `nas`,
`shaping_profile`, `session`

## Health
| Method | Path |
|---|---|
| GET | `/health` (นอก `/api/v1`) → `{status: "ok"\|"error", database}` |
