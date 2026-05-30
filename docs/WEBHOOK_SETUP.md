# Cau hinh Webhook Facebook (Meta Developer)

## 1. Bien moi truong (.env)

```env
FB_WEBHOOK_VERIFY_TOKEN=verify-token
FB_APP_SECRET=<app_secret_tu_meta_app_settings_basic>
```

Sau do restart:

```powershell
docker compose up -d --force-recreate webhook-service
```

## 2. Dang ky webhook tren Meta

1. Vao [Meta for Developers](https://developers.facebook.com/) -> chon App.
2. **Webhooks** -> **Page** -> **Subscribe to this object**.
3. **Callback URL** (can public URL, vi du ngrok):
   - `https://<domain-cua-ban>/webhook`
   - Local test: `ngrok http 3001` -> `https://xxxx.ngrok.io/webhook`
4. **Verify Token**: nhap dung gia tri `FB_WEBHOOK_VERIFY_TOKEN` (mac dinh `verify-token`).
5. Subscribe cac field:
   - `feed` (comment tren bai viet)
   - `messages` (Messenger)
6. Chon Page can lang nghe va **Subscribe**.

## 3. Schema normalize (raw_events)

Ca comment va Messenger deu ra cung schema:

| Field | Comment | Messenger |
|-------|---------|-----------|
| event_type | comment_created | message_created |
| channel | comment | messenger |
| comment_id | co | null |
| message_id | null | co (mid) |
| user_id | nguoi comment | nguoi nhan tin |
| message | noi dung text | noi dung text |

## 4. Test local (khong can Facebook that)

Verify handshake:

```powershell
curl.exe -i "http://localhost:3001/webhook?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge=12345"
```

Test POST co chu ky HMAC (comment + messenger):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test-webhook.ps1
```

Unit test normalize:

```powershell
python -m unittest tests.test_webhook_normalize -v
```

## 5. Bang chung nen chup khi nop bai

- Meta Webhook dashboard: subscribed fields `feed`, `messages`
- curl verify tra `200` + challenge
- POST webhook tra `{"status":"ok","published":1}`
- Kafka topic `raw_events` co ca `comment_created` va `message_created`
