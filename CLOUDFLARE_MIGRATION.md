# Córtex Ofertas — Migração para Cloudflare Pages

> Runbook histórico. Cloudflare Pages é a origem canônica atual em
> `https://cortex-ofertas.pages.dev`; Vercel não é fallback de publicação e
> permanece apenas como legado/telemetria. Uma nova publicação continua sujeita
> aos gates de recovery e não é autorizada por este documento.

## Objetivo
Registrar o fluxo usado para migrar a hospedagem pública da Córtex Ofertas para Cloudflare Pages.

## Arquitetura alvo
GitHub (`Hennanst/cortex-marketing-site`) → GitHub Actions → Cloudflare Pages (`cortex-ofertas`) → domínio definitivo após QA.

## Estratégia
- Direct Upload via Wrangler, acionado por GitHub Actions.
- Preview e revisão independente antes de produção.
- Produção somente após autorização do SHA exato, implantação e smoke test.
- O pacote publicado deriva de `data/publication-manifest.json`; todo HTML fora
  dele precisa estar classificado na quarentena e não entra em `dist`.

## Secrets obrigatórios no GitHub
No repositório, em Settings → Secrets and variables → Actions → Repository secrets:

1. `CLOUDFLARE_ACCOUNT_ID`
2. `CLOUDFLARE_API_TOKEN`

O token Cloudflare deve ter, no mínimo, permissão **Account → Cloudflare Pages → Edit** para a conta escolhida.

## Fluxo histórico de primeira implantação
1. Configurar os dois secrets acima.
2. Abrir Actions → `Deploy Córtex to Cloudflare Pages`.
3. Executar `Run workflow` na branch `migrate/cloudflare-pages-20260904` para criar/validar um preview.
4. Validar Home, Setup & Games, imagens, links, disclosures e responsividade no `pages.dev`.
5. Só depois integrar a branch em `main`.
6. O push em `main` fará a implantação de produção e smoke test automático.
7. Canonical/DNS só devem ser alterados depois do Public Render Gate.

## Rollback
Para uma candidata nova, não promover o SHA se Cloudflare ou a QA falharem. O
rollback deve usar um artefato Cloudflare previamente aprovado; não redirecionar
para a origem Vercel legada.

## Projeto Cloudflare
Nome operacional sugerido: `cortex-ofertas`.
Production branch: `main`.

## Estado operacional
CF0 credenciais configuradas pelo usuário em 2026-09-04. Push de validação disparado nesta branch para criar o primeiro preview Cloudflare Pages sem alterar produção.
