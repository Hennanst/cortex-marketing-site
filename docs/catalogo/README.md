# Expansão comercial da Córtex — 08/09/2026

Estado: implementação candidata. Não é aprovação editorial independente, autorização de merge ou comprovação de conversão.

## Decisão editorial

Aprofundar os quatro contextos existentes antes de abrir nichos novos. A nova seleção tem 40 produtos distintos, dez por contexto; cores e repetições entre nichos não contam como ampliação. A variedade atende decisões de compra diferentes e permite comparar alternativas de uma mesma função.

| Contexto | Produtos | Funções cobertas |
|---|---:|---|
| Setup & Games | 10 | Mouse, teclado ABNT2, mousepad, áudio e monitores |
| Trabalho & Estudo | 10 | Notebook, periféricos, chamadas, expansão USB, armazenamento e segunda tela |
| Creator & Streaming | 10 | Webcams, microfones, captura HDMI e controles de atalhos |
| Casa Inteligente | 10 | Tomada, câmeras, iluminação, rede, voz e controle infravermelho |

## Implementação

- Nova vitrine com 40 fotos exatas, escolha por necessidade, limitações visíveis, análises expansíveis, alternativa e orientação de custo-benefício.
- Onze comparações: mouses, monitores, headsets, webcams, câmeras, speakers Alexa, hubs, microfones USB/XLR, QuadCast 2/2 S, Stream Deck Mini/MK.2 e armazenamento interno/externo.
- Quatro hubs com dez produtos cada e guias correspondentes.
- Todos os 14 guias receberam ligações contextuais e imagens pertinentes. Os três guias de notebook gamer mostram contexto editorial e explicitam que o notebook selecionado para produtividade não é uma indicação gamer.
- Início, Sobre e Metodologia explicam pesquisa documental, critérios de qualidade, valor e relação comercial.
- Removidas instruções internas do texto destinado ao comprador. Nenhum preço, estoque, estrela, nota, desconto ou teste próprio foi inventado.

## Evidências e preservação

Os quatro arquivos `*-sources-20260908.json` preservam ASIN, modelo, variante, URL exata da imagem, fontes e verificações de aquisição. Foram identificados 31 conjuntos de imagem/identidade nesta expansão (30 produtos novos e a foto do Smart Plug já comercial). A identificação dos anúncios brasileiros foi confirmada por respostas públicas contendo o título/modelo e o ASIN; HTTP 200 isolado não foi tratado como prova.

Os dez ASINs comerciais anteriores permanecem. As nove fotos comerciais anteriormente aprovadas são preservadas. Não se recuperou em massa nenhuma das 757 páginas legadas em quarentena.

Ressalvas relevantes: K380s usa layout US; G213 usa ABNT2; Deco M4 é uma unidade; Anker 332 não promete HDMI 4K60; Wave DX exige cadeia XLR; controles do AM8 têm limitações no modo XLR; potência da L530E e velocidade agregada do Archer C6 foram omitidas por divergências nas fontes. Fotos são de produtos exatos, sem substituição por imagem gerada.

## Validação e publicação

O build continua apenas empacotando e validando. `render_curated_catalog.py`, `expand_catalog_20260908.py` e `link_curated_guides.py` são ferramentas explícitas de autoria; nenhum workflow as executa. O HTML resultante é versionado e serve como entrada do build.

Verificações locais executadas: 18 testes Python, 5 testes Node, auditoria de 784 HTML (27 públicos e 757 em quarentena), integridade das 40 fichas, links internos/âncoras e tags/rel comerciais. O pacote contém somente as páginas autorizadas e os recursos referenciados. O relatório específico está em `source-validation.json`.

A revisão independente deve examinar o commit e as capturas mobile/desktop do PR exatos antes do merge. A publicação segue no projeto Cloudflare existente. Produção, aprovações antigas e schedulers não são alterados pela criação deste candidato.

## Avaliação de prontidão para crescer

Esta expansão resolve a escassez de opções e a ligação fraca entre conteúdo e compra. Não demonstra, por si só, conversão comercial. Depois da aprovação e publicação, cabe um teste controlado de tráfego para páginas específicas. Aumentar nichos novamente só faz sentido com capacidade de manter fontes, ofertas e comparações úteis.

Ainda não há monitoramento de preços em tempo real nem mensuração de cliques de saída no site. A promessa pública foi limitada à pesquisa documental e ao raciocínio de custo-benefício, com consulta da oferta atual na Amazon. Novos nichos, comparação numérica de preços atuais e mensuração são trabalhos posteriores; nenhum scheduler foi criado ou reativado.
