# Zoho CRM (free edition, 3 users)

1. Sign up for Zoho CRM Free. Note your **data centre** (zoho.com / .eu / .in / .sa …) from the URL.
2. Go to `https://api-console.zoho.com` (use your region's domain) → **Add Client → Self Client**.
3. Generate a code with scope `ZohoCRM.modules.ALL`, duration 10 min.
4. Exchange it for a refresh token (once):
   `curl -X POST "https://accounts.zoho.com/oauth/v2/token" -d "grant_type=authorization_code" -d "client_id=ID" -d "client_secret=SECRET" -d "code=CODE"`
   Copy the `refresh_token` from the response.
5. In `.env`:
   ```
   CRM_MODE=zoho
   ZOHO_CLIENT_ID=...
   ZOHO_CLIENT_SECRET=...
   ZOHO_REFRESH_TOKEN=...
   ZOHO_ACCOUNTS_URL=https://accounts.zoho.com   # change to .eu/.in/.sa to match step 1
   ZOHO_API_URL=https://www.zohoapis.com         # .eu / .in / .sa likewise
   ```
6. Send a test message in the dashboard → check **Leads** in Zoho. Records are upserted by Phone (P1) or Email (P2), so repeats update the same lead.

If it fails, the Activity log shows `crm_error` with the reason; the customer reply is still sent.
Picklist fields (Lead Source/Status) are deliberately not written to avoid validation errors.
