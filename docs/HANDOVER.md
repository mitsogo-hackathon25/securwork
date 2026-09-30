# SecurWork — Client Handover Guide (Django Admin)

Daily store operations are managed via the **Django Admin panel** at:

**https://www.securwork.it/admin/**

---

## 1. Logging In

Use the administrator credentials provided at handover. Change your password immediately:

**Admin → Users → your account → change password**

---

## 2. Managing Products

**Store → Products → Add product**

1. Fill in **name** and **description** (Italian tab)
2. Switch to **English** tab (flag icon) and add English translation
3. Set **SKU**, **slug**, assign **categories**
4. In **Product variants** section below, add rows for each size/colour:
   - SKU, size, colour, price, sale price, stock quantity
5. Upload **product images** in the images section
6. Check flags: Featured, New arrival, Bestseller
7. Save

### Inventory

- Stock is managed **per variant** in the variants table
- Edit **stock quantity** directly in the variant list (inline editing supported)
- Stock decreases automatically when orders are placed
- Customers cannot order more than available stock

---

## 3. Managing Categories

**Store → Categories**

- Add/edit categories with Italian and English names
- Set **parent** for subcategories
- Choose **section**: Workwear or Professional
- Upload category image (optional)

---

## 4. Processing Orders

**Orders → Orders**

1. Click an order to view details
2. Change **status**: Pending → Processing → Shipped → Delivered
3. Customer email notifications can be configured (developer setup)

---

## 5. Coupons

**Orders → Coupons**

Create discount codes with percentage or fixed amount, usage limits, and validity dates.

---

## 6. CMS Pages

**CMS → Pages**

Edit content for About, Shipping, Returns, Privacy, Terms, Cookie Policy.

Each page has Italian and English translation tabs. Legal pages contain **draft text** — have a lawyer review before going live.

**Company contact details** (footer, contact page, map) are set via server `.env` variables:

| Variable | Purpose |
|----------|---------|
| `SECURWORK_COMPANY_NAME` | Company name |
| `SECURWORK_COMPANY_VAT` | VAT number |
| `SECURWORK_COMPANY_ADDRESS` | Street address |
| `SECURWORK_COMPANY_CITY` | City / postcode |
| `SECURWORK_COMPANY_PHONE` | Phone number |
| `SECURWORK_MAP_LAT` / `SECURWORK_MAP_LNG` | Map coordinates |
| `CONTACT_EMAIL` | Contact email |

---

## 7. FAQ

**CMS → FAQ items**

Add questions and answers in both languages.

---

## 8. Contact Messages

**CMS → Contact submissions**

View messages sent via the contact form.

---

## 9. Translations

All product names, descriptions, categories, pages, and FAQ use **django-parler**:

- Click the **language tabs** (Italiano / English) when editing any item
- Both languages should be filled for bilingual storefront

The website header has an **IT / EN** switcher for visitors (UI strings are translated automatically).

---

## 10. Payments & Shipping

**Payments** are configured via server environment variables (`.env`):

| Variable | Purpose |
|----------|---------|
| `STRIPE_PUBLISHABLE_KEY` | Stripe public key |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret |
| `SECURWORK_BANK_IBAN` | IBAN for bank transfers |
| `SECURWORK_BANK_BIC` | BIC/SWIFT for bank transfers |

1. Create a Stripe account at [stripe.com](https://stripe.com)
2. Add keys to `.env` on the server
3. Webhook URL: `https://www.securwork.it/api/payments/webhook/stripe/`
4. Events: `checkout.session.completed`, `checkout.session.expired`

**Bank transfer** orders stay pending until you mark them paid in **Orders → Orders**.

**Shipping** defaults: €5.99 flat rate, free over €100 (`SECURWORK_SHIPPING_FLAT_RATE`, `SECURWORK_FREE_SHIPPING_THRESHOLD`).

Order confirmation emails are sent automatically after payment (or when a bank transfer order is created).

---

## 11. Placeholder Content to Replace

- [ ] Company logo and branding
- [ ] Company details in `.env` (address, VAT, phone, map coordinates)
- [ ] Legal pages in CMS (review draft text with lawyer)
- [ ] Demo products (marked `[DEMO]`) — replace with real catalog
- [ ] Stripe live keys and bank details
- [ ] SMTP email credentials for contact form and order emails
- [ ] Newsletter integration

## 12. Going Live

Follow [DEPLOYMENT.md](DEPLOYMENT.md) for VPS setup and [DNS-SETUP.md](DNS-SETUP.md) for Aruba DNS configuration.

After deployment, run `deploy/scripts/deploy.sh` for future updates.

---

## Quick Reference

| Task | Admin path |
|------|------------|
| Add product | Store → Products → Add |
| Edit stock | Store → Product variants |
| View orders | Orders → Orders |
| Edit homepage content | CMS → Pages |
| Manage FAQ | CMS → FAQ items |
| Create coupon | Orders → Coupons |
| View contact messages | CMS → Contact submissions |
