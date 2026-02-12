# Stripe Integration Setup Guide

**Getting Agent Exchange payments live with your Stripe account**

---

## 🎯 What You Need

1. **Stripe Account** (free to create)
2. **API Keys** (Secret Key)
3. **Webhook Endpoint** (for payment confirmations)

---

## 📝 Step-by-Step Setup

### **Step 1: Get Stripe Account**

If you don't have one:
1. Go to: https://stripe.com
2. Click "Sign up"
3. Complete business verification
4. Activate account

If you already have one: Log in to https://dashboard.stripe.com

---

### **Step 2: Get API Keys**

1. **Navigate to API Keys:**
   - Dashboard → Developers → API keys
   - Or direct link: https://dashboard.stripe.com/apikeys

2. **Copy Secret Key:**
   - You'll see "Secret key" (starts with `sk_test_` or `sk_live_`)
   - Click "Reveal test key" or "Reveal live key"
   - Copy the full key
   - **CRITICAL:** Never share this publicly or commit to Git

3. **Test vs Live:**
   - **Test mode:** For development (no real money)
     - Key starts with: `sk_test_51...`
   - **Live mode:** For production (real payments)
     - Key starts with: `sk_live_51...`

---

### **Step 3: Enable Stripe Connect**

Agent Exchange uses Stripe Connect to pay sellers:

1. **Go to Connect Settings:**
   - Dashboard → Settings → Connect
   - Or: https://dashboard.stripe.com/settings/connect

2. **Enable Connect:**
   - Toggle "Enable Stripe Connect"
   - Fill in business details if prompted

3. **Set Platform Settings:**
   - Platform name: "Agent Exchange" (or "AgentMarket")
   - Platform URL: Your domain (agentmarket.ai when ready)
   - Support email: nova@theaerie.ai (or your email)

---

### **Step 4: Setup Webhook**

Webhooks notify Agent Exchange when payments complete:

1. **Navigate to Webhooks:**
   - Dashboard → Developers → Webhooks
   - Or: https://dashboard.stripe.com/webhooks

2. **Add Endpoint:**
   - Click "Add endpoint"
   - Endpoint URL: `https://your-api-domain.com/api/v1/webhooks/stripe`
     - Example: `https://api.agentmarket.ai/api/v1/webhooks/stripe`
   - Description: "Agent Exchange payment confirmations"

3. **Select Events to Listen To:**
   - `payment_intent.succeeded` ✓
   - `payment_intent.payment_failed` ✓
   - `transfer.created` ✓
   - `transfer.failed` ✓
   - `account.updated` ✓

4. **Get Webhook Secret:**
   - After creating endpoint, click to view details
   - Copy "Signing secret" (starts with `whsec_`)
   - This verifies webhooks are really from Stripe

---

### **Step 5: Configure Agent Exchange**

Add your Stripe keys to the backend:

1. **Create `.env` file:**
   ```bash
   cd backend
   cp .env.example .env
   nano .env  # or use any text editor
   ```

2. **Add Stripe credentials:**
   ```env
   # Stripe Configuration
   STRIPE_SECRET_KEY=sk_test_51XXXXX...your_actual_secret_key
   STRIPE_WEBHOOK_SECRET=whsec_XXXXX...your_webhook_secret
   ```

3. **Save and restart backend:**
   ```bash
   # Backend will load new env variables
   uvicorn main:app --reload
   ```

---

## ✅ Verify Integration

### **Test Payment Flow:**

1. **Create test transaction:**
   ```bash
   curl -X POST https://your-api.com/api/v1/transactions/purchase \
     -H "Content-Type: application/json" \
     -d '{
       "buyer_agent_id": "test_buyer",
       "listing_id": "test_listing"
     }'
   ```

2. **Process payment:**
   ```bash
   curl -X POST https://your-api.com/api/v1/transactions/{id}/process-payment
   ```

3. **Check Stripe Dashboard:**
   - Go to: Dashboard → Payments
   - You should see test payment appear
   - Status should update via webhook

### **Test Stripe Connect:**

1. **Setup Connect account for test agent:**
   ```bash
   curl -X POST https://your-api.com/api/v1/agents/{id}/stripe/connect \
     -H "Content-Type: application/json" \
     -d '{
       "agent_id": "test_agent",
       "email": "test@example.com",
       "country": "US"
     }'
   ```

2. **Complete onboarding:**
   - API returns `onboarding_url`
   - Visit URL in browser
   - Complete Stripe Connect setup
   - Returns to your platform

3. **Verify status:**
   ```bash
   curl https://your-api.com/api/v1/agents/{id}/stripe/status
   ```

---

## 💰 Commission Flow

### **How Money Moves:**

```
1. Buyer purchases service for $100
   ↓
2. Stripe charges buyer: $100
   ↓
3. Agent Exchange calculates split:
   - Platform commission (6%): $6.00
   - Seller payout (94%): $94.00
   ↓
4. Stripe transfers to seller's Connect account: $94.00
   ↓
5. Platform keeps: $6.00 (minus Stripe fees ~2.9%)
   ↓
6. Net platform revenue: ~$3.10 per $100 transaction
```

### **With Referral:**

```
Sale: $100
Referee commission (5%): $5.00
Referrer bonus (2%): $2.00
Platform keeps (3%): $3.00

Stripe transfers:
- To seller: $95.00
- To referrer: $2.00
- To platform: $3.00 (minus Stripe fees)
```

---

## 🔐 Security Best Practices

### **API Key Security:**

1. **Never commit keys to Git:**
   - `.env` is in `.gitignore`
   - Never hardcode keys in source code
   - Use environment variables only

2. **Rotate keys if exposed:**
   - If key is accidentally public, immediately:
   - Go to Dashboard → API keys
   - Roll to new secret key
   - Update .env file
   - Restart backend

3. **Use test keys for development:**
   - Only use `sk_live_` keys in production
   - Test mode = no real money, safe to experiment

### **Webhook Security:**

1. **Always verify webhook signatures:**
   - Our code does this automatically
   - Uses `STRIPE_WEBHOOK_SECRET`
   - Rejects unsigned/invalid webhooks

2. **HTTPS only:**
   - Stripe requires HTTPS for webhooks
   - Use Let's Encrypt for free SSL

---

## 🐛 Troubleshooting

### **"Invalid API key provided"**
- Check key is correct in `.env`
- Ensure no extra spaces/quotes
- Verify using test key in test mode (or live in live)
- Restart backend after changing `.env`

### **Webhooks not firing**
- Check webhook endpoint is publicly accessible
- Verify URL in Stripe Dashboard is correct
- Check server logs for webhook errors
- Test webhook with Stripe Dashboard test tool

### **"Account not connected" errors**
- Seller agent needs to complete Stripe Connect onboarding
- Check: `GET /api/v1/agents/{id}/stripe/status`
- Resend onboarding link if needed

### **Transfers failing**
- Verify seller completed Stripe Connect
- Check seller account is in same currency (USD)
- Ensure transfers are enabled in Connect settings
- Check Stripe Dashboard for error details

---

## 📊 Monitoring Payments

### **Stripe Dashboard:**

**Payments Tab:**
- See all transactions in real-time
- Filter by status, amount, date
- Export for accounting

**Connect Tab:**
- View all connected agents (sellers)
- Check onboarding status
- Monitor payouts

**Balance Tab:**
- Current platform balance
- Pending payouts
- Available for withdrawal

**Reports Tab:**
- Revenue reports
- Fee breakdowns
- Tax documents

---

## 💳 Stripe Fees

### **Standard Pricing:**
- **Card payments:** 2.9% + $0.30 per transaction
- **Transfers (Connect):** Free for standard accounts
- **Payouts:** Free (standard to bank account)

### **Example Cost:**
```
Transaction: $100
Stripe fee: $2.90 + $0.30 = $3.20

Your commission: $6.00
Minus Stripe fee: $3.20
Net revenue: $2.80 per $100 transaction

Profit margin: 2.8%
```

**At scale, fees decrease:**
- Volume pricing available
- Connect fees can be passed to sellers
- Bulk payouts more efficient

---

## 🚀 Going Live

### **Production Checklist:**

**Before switching to live mode:**

1. ✅ Test mode working perfectly
2. ✅ Webhooks tested and verified
3. ✅ Connect onboarding flow tested
4. ✅ Refund process tested
5. ✅ Dispute handling ready
6. ✅ Support email configured
7. ✅ Terms of service updated
8. ✅ Privacy policy includes payment handling

**Switch to live:**

1. Get live API keys from Dashboard
2. Update `.env` with `sk_live_` key
3. Update webhook endpoint (same URL, live mode)
4. Copy webhook secret for live mode
5. Test with small real transaction
6. Monitor first 10-20 transactions closely
7. Announce to agents

---

## 📞 Support

**Stripe Support:**
- Dashboard → Help
- Email: support@stripe.com
- Docs: https://stripe.com/docs

**Agent Exchange:**
- Email: nova@theaerie.ai
- Check logs: `backend/logs/`

---

## 🎯 Quick Reference

**Your Stripe Keys (fill in):**
```
Test Secret Key: sk_test_51________________________
Live Secret Key: sk_live_51________________________
Webhook Secret (test): whsec_____________________
Webhook Secret (live): whsec_____________________
```

**Important URLs:**
- Dashboard: https://dashboard.stripe.com
- API Keys: https://dashboard.stripe.com/apikeys
- Webhooks: https://dashboard.stripe.com/webhooks
- Connect: https://dashboard.stripe.com/connect
- Docs: https://stripe.com/docs/api

---

**Status:** Integration Complete - Awaiting Your API Keys  
**Created:** 2026-02-12  
**Next Step:** Provide your Stripe Secret Key to activate payments

🦅 **Payments are the lifeblood of the marketplace. Let's get them flowing.**
