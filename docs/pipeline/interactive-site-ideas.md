# Идеи интерактивности сайта HowToLiveBetter

Черновик брейншторма + **актуальные решения** (fork dlgrv). Ops: [deploy-book-api.md](deploy-book-api.md).

Контекст: книга на `https://book.dlgrv.com` (статика); API `https://api.dlgrv.com` — Go binary `htlb-api` (PocketBase as framework). GitHub Pages — редирект на book.

---

## Цели (выбранные)

| Код | Цель |
|-----|------|
| a | Помочь выбрать «что читать / делать сейчас» |
| b | Увидеть, что полезно другим (соцсигнал) |
| d | Удержание: повод вернуться на сайт |

---

## Backend (committed)

- **Стек:** Go module [`api/`](../../api/), PocketBase library, SQLite `pb_data`, nginx TLS.
- **Host:** `api.dlgrv.com` (не path на book).
- **Routes:** только `/api/htlb/v1/...` (авто-CRUD коллекций закрыт).
- **Auth:** только Google + GitHub OAuth; без email/password.
- **Guest:** `X-HTLB-Sync` + one-time `?sync=` claim; после OAuth — merge guest→user.
- **«Полезно»:** голос только после OAuth (Google/GitHub); счётчики публичные для всех.
- **CI/CD:** GitHub Actions → dlgrv (rsync book + binary).

---

## Что в актуальном MVP (committed)

### 1. Соцсигнал «Полезно»

- Кнопка на карточке (подпись `Полезно (N)`, всегда со счётчиком); без `·` и без `✓`.
- Счётчики публичные (GET); голосовать только OAuth user (POST → 401 без Bearer).
- Страница «Мои Полезно»: `GET /useful/mine` + `site/useful/` из меню аккаунта.
- Top + «На этой неделе» — ещё не в этом MVP.

### 2. Закладки на бэке

- После guest session или OAuth; фильтр в сайдбаре; локальный кэш + API.

### 3. Позиция чтения на бэке

- Debounce на API; resume кросс-девайс через guest/OAuth.

### 4. Identity

- Guest: `htlb_sync_token` + one-time claim link «Другое устройство».
- OAuth: Google / GitHub; merge при логине.
- «Полезно»: читать без токена; голосовать — только OAuth Bearer.

### UI (v2)

- Editorial minimal; graceful degrade если API down; без middle dot `·`.

---

## Хостинг

| Host | Роль |
|------|------|
| `book.dlgrv.com` | статика на dlgrv |
| `api.dlgrv.com` | htlb-api |
| `dlgrv.github.io/HowToLiveBetter` | redirect → book |

---

## HTTP surface (кратко)

Prefix: `https://api.dlgrv.com/api/htlb/v1`

- `GET /health`
- `POST /guest/session`, `POST /guest/claim`
- `GET|POST /useful`
- `GET|PUT|DELETE /bookmarks`, `GET|PUT /reading`
- `POST /merge` (OAuth + guest token in body)

CORS: `https://book.dlgrv.com` (+ localhost только в dev).

---

## Явно не делаем (сейчас)

- Password / email signup
- Комментарии, digests, мастер ситуации
- Cloudflare Worker как API
- Открытый PB collection CRUD
- Разделитель `·` в новом UI

---

## Связанные пути

- `api/` — Go backend
- `deploy/` — nginx, systemd
- `site/`, `forge/site/build_pages.py` — UI / HOST
- [deploy-book-api.md](deploy-book-api.md)

---

## Краткая история решений

1. Интерактив a/b/d → useful + bookmarks + position.
2. Backend: PocketBase Go framework на dlgrv (не CF Worker, не JS hooks).
3. Dual identity: guest claim + OAuth Google/GitHub only.
4. API host `api.dlgrv.com`; book на dlgrv; Pages = redirect.
5. Custom routes only; `X-HTLB-Sync` для guest.
