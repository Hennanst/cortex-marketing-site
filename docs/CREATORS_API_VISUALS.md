# Amazon Creators API — exact product visuals for Córtex

Status: PRE-PRODUCTION / G-IMG-01P remediation
Branch: `feat/creators-api-visuals-20260905`

## Why this exists

G-IMG-01P prohibits treating generic/context photography as a premium visual for a named SKU. The current public site is transparent about those images, but G305, G203 and IdeaPad remain product-visual HOLD until the image itself is tied to the exact destination ASIN through a rights-safe source.

Amazon Creators API is the preferred catalog source because it can return the exact product title, detail-page URL and Amazon-hosted image URLs for an ASIN under the Associates program.

## Current external access gate

Amazon's current Creators API documentation requires the Associates account to be eligible for API access, register for Creators API and generate Creators API credentials. Amazon currently states that access requires at least 10 qualifying sales in the previous 30 days. Existing PA-API/AWS credentials are not Creators API credentials.

Nothing in this repository can bypass that account-level eligibility gate.

## Córtex route invariants

- Marketplace: `www.amazon.com.br`
- Partner tag: `cortexofertas-20`
- Credential version default: `3.1` (NA token endpoint; BR belongs to the NA authentication region)
- API base: `https://creatorsapi.amazon`
- GetItems: `POST /catalog/v1/getItems`
- Product images requested: `images.primary.large`, `images.variants.large`
- Product title requested: `itemInfo.title`

The adapter fails closed if the partner tag or marketplace drifts.

## Secrets

The code expects credentials only through environment variables:

- `AMAZON_CREATORS_CLIENT_ID`
- `AMAZON_CREATORS_CLIENT_SECRET`

Optional configuration:

- `AMAZON_CREATORS_VERSION` (default `3.1`)
- `AMAZON_PARTNER_TAG` (must remain `cortexofertas-20`)
- `AMAZON_MARKETPLACE` (must remain `www.amazon.com.br`)

Never commit credential values, paste them into public logs, or expose access tokens in generated manifests.

## Exact products currently targeted

- Logitech G305 LIGHTSPEED — ASIN `B07GPRWFC5`
- Logitech G203 LIGHTSYNC — ASIN `B087CT8PWY`
- Lenovo IdeaPad candidate — historical ASIN `B0D6HXDRZL` — destination must be revalidated before activation

## Safe rollout sequence

1. Keep production on the current Cloudflare release.
2. Confirm Creators API eligibility and create credentials in Associates Central.
3. Store credentials as repository secrets, never in source.
4. Run the non-production exact-ASIN validation workflow.
5. Require exact returned ASIN, title, detail URL and primary image URL.
6. Verify image dimensions and product identity against the intended card/destination.
7. Build a catalog manifest without secrets/tokens.
8. Integrate exact product visuals into one coherent premium visual release batch.
9. Run G-IMG-01P, mobile/desktop public render QA and G9.
10. Only then reconsider SITE_READY/G10.

## Official references

- Creators API introduction: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction
- Using cURL / OAuth and endpoints: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/get-started/using-curl
- Images resources: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/api-reference/resources/images
- Brazil locale: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/locale-reference/brazil
- Migration from PA-API: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/migrating-to-creatorsapi-from-paapi
