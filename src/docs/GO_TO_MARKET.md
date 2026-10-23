# Turning the kit into a product you can sell

This is the operator's manual: how to go from this folder to "someone pays $250, gets a download
and a key, books a Zoom, and gets support" — with the least moving parts. Nothing here is legal or
tax advice; the two places where you need a professional are marked.

## 0. The shape of the product

| Piece | What the customer gets | What you run |
|---|---|---|
| Download | `grocery-llm-eval-<version>.zip` (built by `make_release.py`) | a file host (your storefront hosts it) |
| License key | `GLE1-...` string, verified offline inside the kit | `license/licensetool` to issue keys |
| Zoom session | 30 minutes, booked by the customer | a Calendly/Cal.com/Zoom scheduling link |
| Support | email, 30 days | a support mailbox |
| Updates | new zip + same key for 12 months | re-run `make_release.py`, upload, email customers |

Keys never expire the software. The `expires` date in the key is the end of updates and support.
That keeps refunds, chargebacks and "my key stopped working" tickets to a minimum.

## 1. Pick a storefront (one afternoon)

You want payment, tax handling, file delivery and a receipt email without writing code. Any of
these do all four; pick the one whose fees and country support fit you:

* **Lemon Squeezy** — merchant of record (they handle sales tax/VAT worldwide), digital downloads,
  built-in license keys (you can use theirs *or* paste yours into the receipt), ~5% + fees.
* **Gumroad** — simplest setup, merchant of record, handles VAT, ~10% fee.
* **Stripe Payment Links + Stripe Tax** — lowest fees, but you handle delivery yourself (e.g. a
  Zapier/Make automation or a small script that emails the key after `checkout.session.completed`).
* **Paddle** — merchant of record, good for B2B invoices.

Decision rule: if you do not want to think about sales tax in other countries, use a merchant of
record (Lemon Squeezy, Gumroad, Paddle). Register the product as a digital download, price $250,
and upload the zip from step 4.

## 2. Set up the three links

1. **Checkout URL** from your storefront → put it in `web/buy.html` in place of
   `CHECKOUT_URL_PLACEHOLDER`. Also replace `SUPPORT_EMAIL_PLACEHOLDER` and
   `SELLER_NAME_PLACEHOLDER` (buy.html, LICENSE-EULA.txt, web/eula.html).
2. **Booking link** (Calendly, Cal.com, SavvyCal, or Zoom's own scheduler): a 30-minute event type,
   availability limited to the hours you want, buffer between calls, and a question field
   "What is your order number and what would you like to cover?". Put the link in the purchase email.
3. **Support mailbox**: a dedicated address (support@yourdomain) forwarded to you. Reply template in
   section 6.

## 3. Create your signing key and issue licenses (15 minutes)

```
cd license
go build -o licensetool .          # or: go run . <command>
./licensetool keygen               # prints the PUBLIC key, writes seller_private.key
```

Paste the public key into the four places that verify keys (they must all match):

* `license/main.go`            → `PublicKeyHex`
* `server/license.go`          → `licensePublicKeyHex`
* `grocery_eval/license.py`    → `PUBLIC_KEY_HEX`
* `web/license.js`             → `PUBLIC_KEY_HEX`

The kit ships with a DEMO key pair (`license/demo_private.key`, demo key in
`docs/DEMO_LICENSE_KEY.txt`) so the flow can be tried end to end. **Replace it before selling**:
anyone with the demo private key could issue keys for a product that still uses the demo public key.
`make_release.py` refuses to build a release while the demo public key is in place.

Back up `seller_private.key` somewhere safe (password manager). It is never shipped; `.gitignore`
and `make_release.py` both exclude it. If it leaks, generate a new pair, update the four files,
ship an update, and re-issue keys to customers.

Issue a key for each sale:

```
./licensetool issue -name "Jane Doe" -email jane@example.com -plan personal -years 1
./licensetool issue -name "Acme QA" -email qa@acme.com -plan team -seats 5 -years 1
```

Every key is appended to `issued_keys.jsonl` (your ledger). To check a key a customer sends you:
`./licensetool verify GLE1-...`.

**Automating it.** With Lemon Squeezy/Gumroad you can (a) issue keys by hand from the order email
— fine up to a few sales a day — or (b) run a small webhook receiver that calls `licensetool issue`
and emails the key. Option (a) first; automate when it hurts.

**Optional activation ledger.** `./licensetool serve -addr :9090` runs a tiny server with
`POST /activate` (records who activated, from where) and `GET /activations`. The kit does *not*
require it — verification is offline — but you can point a future version at it if you want
activation counts or remote revocation (add a key id to `revoked.txt`).

## 4. Build the release zip

```
python make_release.py --version 1.0.0
```

This creates `dist/grocery-llm-eval-1.0.0.zip` containing the kit without: private keys, the demo
key, `issued_keys.jsonl`, results folders, `.git`, caches and the sales page. It also writes
`VERSION` and `CHANGELOG.md` into the zip and runs the scorer self-test first. Optionally add
prebuilt server binaries so customers do not need Go:

```
cd server && GOOS=windows GOARCH=amd64 go build -o ../dist/bin/grocery-server-windows.exe .
            GOOS=darwin  GOARCH=arm64 go build -o ../dist/bin/grocery-server-mac-arm64 .
            GOOS=linux   GOARCH=amd64 go build -o ../dist/bin/grocery-server-linux .
python make_release.py --version 1.0.0 --with-binaries
```

Upload the zip to the storefront as the product file.

## 5. Host the sales page

`web/buy.html` is static: host it anywhere (Netlify, Cloudflare Pages, GitHub Pages, your own
site). It needs `common.js` next to it. The tutorial (`index.html`) can be public too — it is the
best advertisement, and trial mode is designed for exactly that. Keep `lab.html` public or not as
you prefer; it is useless without a local Ollama anyway.

Suggested public site: `index.html` (tutorial, free) → `buy.html` → storefront checkout.

## 6. The purchase email and support templates

**Purchase email** (storefront receipt or your own):

> Subject: Your Grocery-Store AI Test Kit — download, license key and Zoom booking
>
> Thanks for your purchase, {name}. Here is everything you need:
> 1. Download: {link}  (version {version})
> 2. Your license key (keep this email):  `{key}`
>    Activate by pasting it into the Live Lab page, or run `python activate.py {key}` in the kit folder.
> 3. Book your 30-minute Zoom session (within 90 days): {booking link}
> 4. Support for 30 days: reply to this email or write to {support email}. Order number: {order}.
> Start with README.md, then TUTORIAL.md (or open web/index.html). Updates for 12 months will be
> sent to this address.

**Support reply template:** acknowledge within 2 business days; ask for OS, the output of
`check_tools` and the `results.jsonl` row if it is a scoring question; link to the relevant
tutorial section; offer the Zoom if it is a setup problem.

**Zoom session structure (30 min):** 5 min what they want to achieve → 15 min screen-share
(setup or reading their first report) → 10 min how to adapt the kit to their own data, next steps.

## 7. Legal and money (talk to a professional for these two)

* **Terms:** `LICENSE-EULA.txt` is a plain-language template; have a lawyer check it for your
  jurisdiction and fill the placeholders. Publish it as `web/eula.html` (included) and link it from
  the checkout.
* **Taxes:** a merchant-of-record storefront collects sales tax/VAT for you; with Stripe you must
  configure Stripe Tax and register where required. Income tax is yours either way.
* **Trademarks:** the sales page states that Ollama, DeepSeek, Llama and Gemma belong to their
  owners. Do not use their logos.
* **Refunds:** the policy on the sales page (14 days if it will not run) is deliberately narrow
  because the product is source code. Honour chargebacks promptly; revoke the key in your ledger.

## 8. Pricing and packaging notes

* $250 personal includes the 30-minute call — the call is the expensive part. Cap the booking
  window (90 days) so obligations do not pile up, and keep 2–3 slots a week.
* Team (5 seats, one group call): $900 is a reasonable anchor; invoice by email at first.
* Later options: a "no call" tier at $149, or a workshop tier at $750 with a 2-hour session.
* The free tutorial with a simulated model is the funnel. Trial mode on the real tools is the
  second step. Do not weaken either; they do the selling.

## 9. Release checklist

- [ ] Real signing key generated; public key pasted into all four files; demo key removed
- [ ] `python run_eval.py --self-test` passes; `node web/license.js` smoke test passes
- [ ] Placeholders replaced in `buy.html`, `eula.html`, `LICENSE-EULA.txt`
- [ ] `python make_release.py --version X.Y.Z` built and the zip opened on a clean machine
- [ ] Storefront product created, zip uploaded, test purchase made with a 100% coupon
- [ ] Purchase email contains download, key, booking link, support address
- [ ] Booking link tested end to end
- [ ] CHANGELOG.md updated
