# Exact product visuals for Córtex — Amazon-authorized paths

Status: PRE-PRODUCTION / G-IMG-01P remediation
Branch: `feat/creators-api-visuals-20260905`

## Why this exists

G-IMG-01P prohibits treating generic/context photography as a premium visual for a named SKU. The current public site is transparent about those images, but G305, G203 and IdeaPad remain product-visual HOLD until the image itself is tied to the exact destination ASIN through a rights-safe source.

## Preferred path: Amazon Creators API

Amazon Creators API is the preferred programmatic catalog source because it can return the exact product title, detail-page URL and Amazon-hosted image URLs for an ASIN under the Associates program.

### Current external access gate

Amazon's current Creators API documentation requires the Associates account to be eligible for API access, register for Creators API and generate Creators API credentials. Amazon currently states that access requires at least 10 qualifying sales in the previous 30 days. Existing PA-API/AWS credentials are not Creators API credentials.

Nothing in this repository can bypass that account-level eligibility gate.

## Official fallback without Creators API: Amazon SiteStripe Image link

Amazon Associates Brazil currently documents `Obter link: Imagem` in SiteStripe. It creates an image link for the exact Amazon product page being viewed and includes the selected Associate/tracking ID in the generated link. Amazon also documents product-link tools that can generate image-only or text+image product links.

For Córtex, an exact-product visual generated through SiteStripe can enter G-IMG-01P only when all of the following are captured in the manifest:

- `source_type = amazon_sitestripe_image_link`;
- exact ASIN matches the named card;
- destination is `https://www.amazon.com.br/dp/<ASIN>...`;
- destination contains `tag=cortexofertas-20`;
- `rights_basis` explicitly records Amazon Associates SiteStripe image-link generation;
- `source_ref` uses the Córtex provenance form `sitestripe:<ASIN>:<evidence-id-or-timestamp>`;
- image URL is Amazon-hosted;
- image long edge is at least 800 px under the current premium threshold;
- image is unique to that named product and is not reused by hero/category imagery.

If the official SiteStripe output does not provide enough image resolution for the 800 px premium threshold, the product visual remains HOLD rather than silently lowering the gate.

This fallback does not require scraping Amazon product pages and must use only the image/link output produced by the Associate tool itself.

## Other allowed exact-image paths

- Manufacturer media with explicit documented permission for the exact affiliate-site use.
- Owner-supplied original exact-product photography with provenance.

Public visibility, press-page presence, retailer pages and generic media kits are not sufficient rights evidence by themselves.

## Córtex route invariants

- Marketplace: `www.amazon.com.br`
- Partner tag: `cortexofertas-20`
- Credential version default for Creators API: `3.1` (NA token endpoint; BR belongs to the NA authentication region)
- Creators API base: `https://creatorsapi.amazon`
- GetItems: `POST /catalog/v1/getItems`
- Product images requested: `images.primary.large`, `images.variants.large`
- Product title requested: `itemInfo.title`

The adapter and manifest validator fail closed if the partner tag or marketplace drifts.

## Secrets for Creators API

The code expects credentials only through environment variables:

- `AMAZON_CREATORS_CLIENT_ID`
- `AMAZON_CREATORS_CLIENT_SECRET`

Optional configuration:

- `AMAZON_CREATORS_VERSION` (default `3.1`)
- `AMAZON_PARTNER_TAG` (must remain `cortexofertas-20`)
- `AMAZON_MARKETPLACE` (must remain `www.amazon.com.br`)

Never commit credential values, paste them into public logs, or expose access tokens in generated manifests.

SiteStripe does not require Creators API credentials in this repository; it is generated from the authenticated Amazon Associate user interface.

## Exact products currently targeted

- Logitech G305 LIGHTSPEED — ASIN `B07GPRWFC5`
- Logitech G203 LIGHTSYNC — ASIN `B087CT8PWY`
- Lenovo IdeaPad candidate — historical ASIN `B0D6HXDRZL` — identity is corroborated, but live availability must remain retailer-time data

## Safe rollout sequence

1. Keep production on the current Cloudflare release.
2. Try a rights-safe exact-product source in this order: Creators API if eligible, SiteStripe Image link, explicit manufacturer permission, owner-supplied original exact-product photography.
3. Build `cortex.product-visuals.v1` manifests with exact ASIN, destination, provenance, rights basis, image URL and dimensions.
4. Run `scripts/validate_product_visual_manifest.py` with the current category asset list.
5. Require PASS for every named product being shown visually.
6. Combine the exact-product PASS lane with the already-reviewed hero/category premium lane.
7. Build one coherent release batch and one production deploy.
8. Run G-IMG-01P, full public mobile/desktop visual QA and G9.
9. Only then reconsider SITE_READY/G10.

## Official references

- Amazon Associates Brasil — SiteStripe help: https://associados.amazon.com.br/help/node/topic/GJMMT7G4C8K4Y3AY
- Amazon Associates Brasil — tools / product links: https://associados.amazon.com.br/welcome/topic/tools
- Creators API introduction: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction
- Using cURL / OAuth and endpoints: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/get-started/using-curl
- Images resources: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/api-reference/resources/images
- Brazil locale: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/locale-reference/brazil
- Migration from PA-API: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/migrating-to-creatorsapi-from-paapi
