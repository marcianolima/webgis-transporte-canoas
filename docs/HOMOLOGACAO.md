# Relatório técnico — revisões de 30–31/10/2026

## Revisão 0.4.0 — cobertura das paradas em 31/10/2026

**1.410 paradas**, mais 1.025, dos 1.433 IDs das 72 listas consultadas (98,39%). Outros 23 IDs retornaram posições fora da área de referência e foram separados para revisão; nenhuma consulta ficou pendente nesse recorte. Preservados os 385 IDs, 1.386 vínculos e os 57 itinerários anteriores. Duas rodadas com 386 respostas válidas e 416 usos de cache, sem falhas/retries. Mapas de paradas/km² e área a 300 m, completude e exportações por linha. [Relatório e limites](COBERTURA-PARADAS.md).

Validação local: **128 testes Python, 30 TypeScript/React**, lint, build e dados públicos aprovados. Evidência em `research/stop-coverage-2026-10-31.json`. A conclusão do deploy remoto desta revisão será registrada após conferir o run correspondente. O recorte não constitui inventário municipal homologado nem monitoramento GPS.


## Revisão 0.3.1 — retomada em 31/10/2026

A retomada da API respondeu HTTP 200; coleta concluída com 77 requisições, 114 usos de cache e nenhuma falha. Publicação mesclada: **57 itinerários de 36 linhas e 385 paradas**, mantendo todos os IDs e vínculos anteriores. PMTiles com 541.915 bytes e 28 tiles. Oito percursos sob revisão de borda. [Resultado, proteção e limites](RETOMADA-COLETA.md).

Validação local: **123 testes Python e 25 TypeScript/React**, lint, build e validação dos dados públicos aprovados. Build e deploy remotos concluídos com sucesso no commit `1edc9b02b7c329645c5bdddf0bdd80227eb44de7`, [run 41199492831](https://github.com/marcianolima/webgis-transporte-canoas/actions/runs/41199492831). O navegador público confirmou PMTiles carregado, 36 linhas, 385 paradas e três traçados simultâneos das linhas 5000/5116; filtro local da 5116 retornou 24 paradas. O arquivo público completo e a leitura Range foram conferidos contra o SHA-256 do manifesto. Evidência em `research/network-retry-2026-10-31.json`. GPS e infraestrutura operacional continuam pendentes.


## Revisão 0.3.0

52 itinerários reais de 35 linhas e 215 paradas TACOM em PMTiles, como referência não homologada operacionalmente. 111 testes Python e 25 TypeScript/React; lint e build locais aprovados. Diagnóstico, correção da amostra de Viamão, métricas, qualidade e limites em [EVOLUCAO-0.3.md](EVOLUCAO-0.3.md). Publicação da 0.3.0 verificada no commit `69bc2ba160f303bca8ca96c5cbc38144dd3a58f6`: [run 41196047057](https://github.com/marcianolima/webgis-transporte-canoas/actions/runs/41196047057), build e deploy concluídos com sucesso. Navegador público confirmou 35 linhas, 215 paradas, PMTiles carregado e desenho simultâneo de 5000/5001. Evidência em `research/release-0.3.0.json`. Os registros a seguir são históricos das revisões anteriores.


## Revisão 0.2.0: mapa PMTiles e seleção de linhas

Implementados: modo compatível sem WebGL, PMTiles v3/MVT local, desenho vetorial Canvas com ampliação vetorial, filtro de uma/várias linhas, cores estáveis, enquadramento, seleção de bairros, mapa na ficha da linha, recuperação GeoJSON e reinicialização. O arquivo real tem 18 bairros, 659 setores, 27 tiles e aproximadamente 263 kB. Manifesto identifica hash, fontes, disponibilidade e generalização. Não depende de mapa OSM ou chave comercial.

Importador GeoJSON/GTFS implementado com join por código exato, agência municipal explícita, coordenadas, validade GTFS quando publicada, proveniência e histórico local por hash. **Não há feed real de percursos homologado: 0/81 linhas com geometria e 0 paradas.** Desenho de percursos foi verificado em fixture sintética isolada e não publicada. Nenhum trajeto foi inferido da lista de logradouros.

Verificações desta revisão: **65 testes Python**, **23 testes TypeScript/React**, ESLint e build de produção aprovados localmente. Testes novos cobrem arquivo PMTiles real, contagens e hashes, tile de Canoas, orientação MVT, determinismo, GeoJSON/GTFS, seleção, busca, limpeza, enquadramento e transporte Range/sem Range/cancelamento/limite. Validação pública: 81 IDs, 4.990 saídas, 5 datas, sem fixtures sintéticas nos dados publicados.

QA visual: PMTiles de bairros/setores carregou no navegador; seleção de bairro enquadrou corretamente; linha sem geometria informou a ausência; fixture isolada desenhou e removeu percurso. Viewport móvel interno 390×844: altura de mapa 440 px, `clientWidth=scrollWidth=375` (15 px de scrollbar). É um viewport de teste, não aparelho físico. WebGL continua indisponível nesse navegador; não se declara homologação visual do motor MapLibre. A falha original em dispositivo do usuário não foi reproduzida; o caminho de inicialização foi substituído por modo compatível e recuperação explícita.

GPS GoBus, ETA, cadastro geográfico e resultados de auditoria operacional continuam pendentes. O avanço no mapa não encerra a engenharia reversa TACOM. [Pendências da 1.0](VERSAO-1.0.md) e [operação PMTiles](MAPA-PMTILES.md).

Publicação 0.2.0 verificada: commit `ea17ef1a932af83bb7bdc27388b6416ed8357b7b`; [run 41147965947](https://github.com/marcianolima/webgis-transporte-canoas/actions/runs/41147965947), build e deploy concluídos com sucesso. A aplicação pública mostrou “Base local PMTiles carregada”, troca para setores e seleção da linha 5000 com aviso de geometria pendente. O arquivo público respondeu **HTTP 206**, `Content-Range: bytes 0-126/263145`; transferência completa de 263.145 bytes com SHA-256 `3649e6b286f04e72fbdb8f5816bf7230f65be6a5f0d9f567d3c3a91c16b16fd1`, igual ao manifesto. Evidência em `research/release-0.2.0.json` (31/10/2026 UTC; 30/10 em Brasília). Um ajuste posterior assegura aplicação das camadas MapLibre após criar as fontes, sem aguardar indevidamente o estado global de carregamento dos workers. Os registros abaixo descrevem a revisão anterior.

## Resultado da revisão anterior (0.1.0)

Versão 0.1.0 com programação real da Sogal/NGS e análise territorial. Repositório inicial possuía somente README (commit `3157eaed939adb63d0e5b9843293ed88dcdad5e1`), na branch `main`, sem código a descartar.

Coleta final: **81 linhas distintas, 4.990 saídas programadas, cinco datas, zero erros**. Registros por data e amostras são verificáveis nos arquivos públicos e no relatório de coleta. Bairros: 18; setores: 659. Todos os registros públicos passaram pela verificação de origem, chaves, horários, coordenadas e ausência de fixtures sintéticas. Produtos públicos somam aproximadamente 4,1 MB sem compressão, antes dos bundles do frontend.

A revisão final também corrigiu o retorno ao topo ao trocar de página e o registro persistente do início de cada coleta. O código de interface foi formatado para facilitar manutenção.

A versão não cumpre ainda os critérios completos da 1.0: a API GPS municipal não foi homologada e o backend municipal não está implantado.

## Testes executados

| Verificação | Resultado observado |
| --- | --- |
| Python / pytest | 57 aprovados |
| TypeScript/React / Vitest | 10 aprovados |
| ESLint | Aprovado |
| TypeScript + Vite build de produção | Aprovado |
| Validação dos dados públicos | 81 IDs, 4.990 saídas, 5 datas; sem dados de teste publicados |
| Contratos NGS | Respostas reais, BOM, datas, cadastro, horários e logradouros validados |
| Histórico e API | SQLite, deduplicação, conflitos, autenticação, escopo, CSV/GeoJSON e revisão testados |
| Navegador desktop | Painel, camadas locais, troca bairros/setores e estados de disponibilidade verificados |
| Viewport móvel 390 × 844 | Página, menu ativo, busca, data, sentidos e relatórios verificados em iframe de QA |
| Estouro horizontal no mobile | `scrollWidth == clientWidth` no fluxo de linhas testado |

O teste móvel usa viewport interno de navegador, não um aparelho físico. Não foi feita auditoria WCAG completa, screen reader ou homologação em todos os navegadores. MapLibre/WebGL não executou no navegador de QA por ausência de WebGL; alternativa Leaflet/SVG foi adicionada e o mapa local foi verificado visualmente. Fundo OSM foi bloqueado no ambiente de teste, permanece opcional e desligado por padrão. Não é utilizada chave CARTO.

Download CSV confirmado no site publicado, com 101 saídas da linha 05000 em 30/10/2026 e conteúdo validado após sincronização. A tentativa anterior dentro do iframe móvel não retornou evento no tempo do teste. Não se declara homologação do download nativo em todos os dispositivos nem do diálogo de impressão/PDF.

Dependências Python emitiram avisos de depreciação de Shapely e TestClient; os testes passaram. Não houve Docker disponível nesta sessão: Compose/PostgreSQL/PostGIS, proxy TLS e worker com fonte GPS real não foram executados.

## Publicação

**Frontend publicado e verificado no GitHub Pages:** https://marcianolima.github.io/webgis-transporte-canoas/ . Commit inicial da implementação: `b49a71e5b1af8db3db9f30fbfcbf9f8deca2f9d3`, enviado à `main` pelo conector GitHub. [Execução inicial de CI e deploy](https://github.com/marcianolima/webgis-transporte-canoas/actions/runs/41141596464): jobs build e deploy concluídos com sucesso. A aplicação pública carregou os dados reais e o relatório filtrado; download CSV também validado. Correção posterior adiciona espaço de rolagem para manter inclusive o último item ativo alinhado à esquerda no menu móvel (posição observada: 13,25 px). A consulta anterior ao primeiro deploy retornava 404; esse bloqueio foi resolvido.

## Dependências que permanecem

1. APK legítimo ou documentação/amostra autorizada da TACOM para confirmar host, código municipal, autenticação e contratos GoBus/TEU. Nenhuma credencial de terceiros ou bypass foi utilizado.
2. Feed municipal de GPS com timestamp de origem, identificação de veículo/linha e frequência autorizada. Worker recebe contrato normalizado próprio; adaptador TACOM real permanece pendente.
3. Cadastro geográfico homologado de paradas, sequência por sentido/variante e shapes temporais. Endpoint de mapa NGS respondeu 404.
4. Identificadores de viagens, ordens de serviço e programação contratual para pontualidade, viagens realizadas e eventuais descumprimentos. Ausência de GPS nunca é classificada como cancelamento.
5. Infraestrutura persistente municipal, TLS, backup e autenticação nominal para fiscalização multiusuário. O código inclui API e painel protegidos por chave técnica, não SSO ou RBAC completo.
6. Fontes/reconciliação para acessibilidade a escolas/saúde, cobertura populacional e oferta por bairro. Setores e bairros estão disponíveis; transporte geográfico ainda não.

## Aceite honesto

Entregue e testado: consulta real de programação, cartografia territorial, fontes/metodologia, coleta/histórico estático e código executável de API/auditoria. Preparado: infraestrutura operacional e modelo PostGIS. Pendente: integração GoBus GPS, implantação externa e homologação operacional municipal. Não declarar a totalidade da 1.0 enquanto essas dependências não forem resolvidas.
