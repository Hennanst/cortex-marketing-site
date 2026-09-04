# Córtex Ofertas — Migração para Cloudflare Pages

## Objetivo
Migrar a hospedagem pública da Córtex Ofertas para Cloudflare Pages sem desligar a Vercel antes da validação do novo ambiente.

## Arquitetura alvo
GitHub (`Hennanst/cortex-marketing-site`) → GitHub Actions → Cloudflare Pages (`cortex-ofertas`) → domínio definitivo após QA.

## Estratégia
- Direct Upload via Wrangler, acionado por GitHub Actions.
- Preview antes do cutover.
- Produção somente quando a branch `main` for implantada e o smoke test passar.
- Vercel permanece como fallback durante a migração.
- O pacote publicado exclui `.git`, `.github`, scripts operacionais e `release-state.json`.

## Secrets obrigatórios no GitHub
No repositório, em Settings → Secrets and variables → Actions → Repository secrets:

1. `CLOUDFLARE_ACCOUNT_ID`
2. `CLOUDFLARE_API_TOKEN`

O token Cloudflare deve ter, no mínimo, permissão **Account → Cloudflare Pages → Edit** para a conta escolhida.

## Fluxo de primeira implantação
1. Configurar os dois secrets acima.
2. Abrir Actions → `Deploy Córtex to Cloudflare Pages`.
3. Executar `Run workflow` na branch `migrate/cloudflare-pages-20260904` para criar/validar um preview.
4. Validar Home, Setup & Games, imagens, links, disclosures e responsividade no `pages.dev`.
5. Só depois integrar a branch em `main`.
6. O push em `main` fará a implantação de produção e smoke test automático.
7. Custom domain/canonical/DNS só devem ser alterados depois do Public Render Gate.

## Rollback
Enquanto o domínio definitivo não for apontado para Cloudflare, nenhuma mudança é necessária no ambiente Vercel. Se o Cloudflare falhar no QA, basta não concluir o cutover.

## Projeto Cloudflare
Nome operacional sugerido: `cortex-ofertas`.
Production branch: `main`.
