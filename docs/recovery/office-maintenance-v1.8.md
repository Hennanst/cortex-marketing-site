# Córtex — manutenção operacional v1.8

Escopo exclusivo CO / Tailwind 1653454. Autorização: pedido do proprietário para
pausar os schedulers e revisar integralmente código, escritório e gates.
Os três schedulers permanecem pausados. Esta entrega é candidata em recovery;
não declara Market Ready, não altera main e não libera aquisição.

## Correções executáveis

- Inventário completo de 784 HTMLs. Normalização literal em 769 arquivos,
  documentada com hashes antes/depois em `normalization-inventory.json`.
  Os hashes finais desse inventário representam a etapa mecânica, anterior às
  correções editoriais pontuais. Nenhuma página legada foi removida da auditoria.
- Mesmo inventário público para empacotamento e comparação byte a byte de todos
  os HTMLs, dados e assets. Documentação, testes e scripts não são publicados.
- Canonical único, origem HTTPS exata e rota correta; ausência de canonical
  também reprova. Domínio parecido não passa por prefixo.
- Build audita antes de criar pacote. Uma falha não transforma material
  incompleto em deploy. Headers são fonte revisável, sem injeção editorial.
- Testes de regressão simulam canonical fraudulento, guia alterado só em dist,
  arquivo ausente/extra, linha reordenada, ID duplicado, estado desatualizado,
  lease vencido, CI não executado, SHA diferente, autorrevisão e ciclo no DAG.
- CI preserva JSON de auditoria com cobertura e lista completa de falhas,
  identificado pelo SHA; falha continua falha. Build pulado não significa PASS.

`scripts/office_control.py` é uma biblioteca verificadora e CLI de schema,
não um daemon nem um conector remoto. Recebe snapshot fresco de CONFIG, GATES,
JOBS, STATE, LOCKS, TRANSACTIONS e RUN_CONTROL, com cabeçalhos. A CLI também
recebe `--plan plano.json --run-id <run_id>` para produzir patches mínimos e
contrato de readback. Os três prompts recebem a exigência de executar a versão
imutável referenciada em CONFIG antes de writes. A integração ainda exige
revisão independente e teste operacional antes da reativação.

O planejador bloqueia scheduler durante manutenção manual, lease alheio ou
vencido, TX já existente, ID/identidade alterados, estado esperado divergente,
campos duplicados e alterações em registros aprovados. Não aprova gates nem
libera operações externas. O chamador deve persistir o artefato, reler lease e
estado, anexar a transação no mesmo batch e conferir cada campo por ID depois.
Sheets não oferece CAS; a biblioteca não transforma esse limite em garantia.

Validação de manutenção: dez testes executados com sucesso e schema validado
contra snapshot de 89 CONFIGs, 65 gates, 13 jobs, 7 estados, 5 locks, 73 TXs
e uma lease. Isso não equivale a um ciclo agendado completo ou aprovação global.

A revisão candidata do manuscrito foi copiada nativamente da v1.3, preservando
o original, e verificada por readback:
https://docs.google.com/document/d/17KM079qeSQgD6ljKdwNc9blVyrMFB1wjUc1PmY6gqs8/edit
Ela permanece candidata enquanto CONFIG e revisão de release não a efetivarem.
O PDF v1.3 continua histórico/canônico da versão vigente; não é PDF da v1.4.

## Proposta formal de reconciliação do release — pendente de revisão

A trava atual de main depende de RG9, que depende de RG8 em produção. Isso
impede alcançar a condição necessária para liberar a própria trava.
Sequência proposta, sem antecipar Market Ready:

1. RG2–RG6: fonte comercial, mídia, canonical e build aprovados no candidato.
2. RG7: CI e preview mobile/desktop do SHA integral executados e revisados.
3. RG7A: autorização de publicação restrita ao SHA, árvore, PR e artefato
   aprovados. Revisão independente da execução que produziu o candidato.
4. Deploy desse candidato em Cloudflare. Proibido usar main para edição.
5. RG8: verificar origem pública, SHA/artefato publicado, rotas, imagens,
   navegação, disclosures e ausência de alteração semântica pelo build.
6. RG9: revisão final Market Ready, seguida de transação explícita RELEASED.
7. RG10: reabrir aquisição; route-check imediato e deduplicação antes de write.

Esta proposta NÃO modifica LOCK-CO-MAIN-WRITE automaticamente. A revisão deve
ser persistida como nova versão normativa e alterar a condição específica da
trava antes de qualquer merge/deploy. A trava de aquisição permanece até RG10.
Se o merge produzir outro SHA, reexecutar CI nesse SHA e verificar a árvore;
nunca atribuir a ele uma execução de outro commit.

## Continuidade e operação saudável

- Usar o Control Plane vivo para escolher alvo, branch, próximo gate e versão.
- Antes de cada escrita: IDs únicos, cabeçalhos, estado esperado, lease vigente.
  Sheets não oferece compare-and-swap através de batchUpdate: leitura seguida
  de escrita não é garantia de exclusão concorrente. Serialização e readback
  permanecem obrigatórios; lease perdido encerra writes da execução.
- Persistir resultado externo antes da transação. Em resposta ambígua ou falha
  de ledger, reconciliar o resultado antes de repetir deploy/Pin/commit.
- Correção técnica pode completar um lote coerente de manutenção. Revisão
  independente é outra execução, sem atrasos artificiais entre subpassos.
- Falha externa registra operação, último erro, tentativas e próximo retry;
  repetição sem mudança de dependência não ocupa todos os próximos ciclos.
- Não refazer pesquisa de domínio já aprovada sem lacuna nova. Aprendizagem
  utiliza mesma janela, baseline, hipótese e uma variável por experimento.
- Opera/Amazon continua a rota autorizada. Link afiliado é determinístico e
  independente da obtenção da imagem. SiteStripe/API não são pré-requisitos.
- Os três IDs e horários existentes devem ser preservados. Retomada só após
  integração, revisão e validação; não reativar pela mera existência do código.

## Pendências conhecidas de conteúdo e verificação

Os quatro cards HyperX Cloud III Wired, Logitech C920s, LG 24GS60F-B e
AOC 24G4/P foram instalados na fonte em fde84212e0b964fe5a000469f440310d936d6615.
Identidade, URLs e dimensões observadas pelo Opera estão em
`four-cards-opera-evidence-20260908.json`. A revisão comercial e visual
independente continua pendente; instalação não equivale a aprovação de gate. G305, G203, Brio e Havit tiveram
imagens exatas instaladas em guias; requerem revisão do novo candidato.

O acervo legado de reviews possui ratings/preços/estoque estáticos e caminhos
históricos. Corrigir URL não valida esses claims. É necessário inventariar a
proveniência comercial e decidir explicitamente a publicação/revisão do acervo.
Não excluir páginas do validador para fabricar PASS.

A QA visual legada exige fornecedor/contagem de imagens específicos e rejeita
SVG editorial, enquanto parte da fonte aprovada usa esses SVGs. Conciliar o
critério visual por função, qualidade real e identidade sem enfraquecer a QA;
fazer inspeção mobile e desktop antes de qualquer liberação.

Concluir essa revisão normativa, integrar guardas aos runners, revisar o
candidato e validar produção são trabalho pendente. Nenhum PASS global é
atribuído por este documento.

## Revisão adicional do guard — 8 de setembro de 2026

A candidata agora rejeita estados compostos que contenham tokens de aprovação
ou publicação (por exemplo, `PASS_QUEUED`), como já fazia para registros
aprovados existentes. Evidência deve declarar `unknown: 0` explicitamente,
com contagens inteiras e execução produtora identificada. Ausência de dados
não representa ausência de pendências. Lease ausente, data inválida ou sem
fuso horário produz rejeição controlada antes da geração de patches.

Doze testes locais passaram, incluindo essas regressões. A referência imutável
ativa em CONFIG ainda aponta para a versão 6825b278; esta revisão de código
ainda precisa ser integrada e verificada no escritório antes de uso operacional.
Nenhum gate, scheduler, configuração ativa ou autorização de release é alterado
por este commit. Continuam pendentes a validação do modo de execução agendado
quando ausente/desconhecido e a verificação da presença e escopo dos locks.

## Canonical e links na QA de deploy — 8 de setembro de 2026

A QA agora usa comparação exata de origem e rota, exige canonical único e
rejeita query, fragmento e credenciais no canonical. Links relativos e absolutos
internos são resolvidos a partir da página efetiva, preservando query e removendo
fragmento. A checagem HTTP cobre todos os destinos internos únicos coletados
nas oito rotas de entrada; foi removido o corte silencioso em 140 destinos.
Isso não constitui rastreamento recursivo de todo o site.

Dois testes Node cobrem domínio por prefixo, duplicidade, rota incorreta e
resolução de links, e passam a executar no CI de recovery. Os doze testes Python
continuam passando. O JavaScript embutido no workflow passou na checagem de
sintaxe. A QA ao vivo não foi executada nesta alteração, pois não houve deploy.
Os critérios legados de imagens ainda precisam de revisão; nenhum gate de
release foi aprovado por esta correção.

## Correções do site — fotos de produtos e destino quebrado

Removidos 4.263 handlers que trocavam fotos da Amazon por fotografias genéricas
do Unsplash em 745 páginas. A alteração preserva os atributos originais de
imagem e os links de compra. O manifesto `image-fallback-repair-20260908.json`
registra cada página com hashes antes/depois e contagem de handlers removidos.
O guard de fonte agora rejeita esse padrão, com teste de regressão.

O guia `guias/cadeira-gamer-vale-a-pena.html` apontava para o arquivo inexistente
`review/B00DJCDRXJ4.html`. O destino foi corrigido para a página existente
`review/B0DJCDRXJ4.html`, cujo título confirma Redragon Office Hela C214-B.

Isso não verifica a disponibilidade de cada imagem remota: falhas reais de
carregamento devem ser reparadas com assets do produto correto. A inspeção
visual local foi tentada com agent-browser, mas seu daemon falhou ao iniciar
inclusive na tentativa de diagnóstico. Não houve aprovação visual nem deploy.
Foram observados atributos HTML antigos com aspas não escapadas em nomes de
produtos; exigem revisão adicional. Os claims comerciais legados continuam
pendentes de revisão de evidência. Schedulers permanecem pausados.
