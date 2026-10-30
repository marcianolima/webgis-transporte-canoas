# Relatório técnico da execução — 30/10/2026

## Resultado efetivo

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
