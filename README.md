# WebGIS Transporte Canoas

Plataforma de informação e análise do transporte coletivo municipal de Canoas/RS, com programação real da Sogal, cartografia local, metodologia aberta e infraestrutura para histórico e fiscalização.

**Versão 0.2.0 — mapa PMTiles local, seleção de linhas e importação de percursos; engenharia reversa estática do APK GoBus concluída, GPS ainda não homologado.** Não é declarado atendimento integral dos critérios da versão 1.0. Não são gerados veículos, paradas, viagens realizadas ou infrações fictícios.

[Aplicação pública](https://marcianolima.github.io/webgis-transporte-canoas/) · [Execuções e deploy](https://github.com/marcianolima/webgis-transporte-canoas/actions) · [Relatório técnico](docs/HOMOLOGACAO.md)

[Homologação TACOM/GoBus](docs/GOBUS-HOMOLOGACAO.md) · [Mapa e importação PMTiles](docs/MAPA-PMTILES.md) · [APK GoBus: relatório de engenharia reversa](docs/APK-GOBUS-1.29.1.2.md) · [Pendências para a versão 1.0](docs/VERSAO-1.0.md)

## Dados efetivamente obtidos

Coleta de 30/10/2026 nos endpoints públicos do portal de horários vinculado pela Sogal:

| Data de serviço | Linhas publicadas |
| --- | ---: |
| 30/10/2026 | 77 |
| 31/10/2026 | 42 |
| 01/11/2026 | 24 |
| 02/11/2026 | 29 |
| 03/11/2026 | 77 |

**81 IDs distintos**, **4.990 saídas programadas**, cinco datas e nenhuma falha na coleta final. A união das linhas varia conforme as datas; não equivale a 81 linhas em operação simultânea. O calendário não é extrapolado. Todas as saídas preservam origem, obtenção e SHA-256 da resposta. Itinerários são sequências **textuais** de logradouros: não foram convertidos em trajetos ou paradas por aproximação.

Bases locais: **18 bairros oficiais** reutilizados do GeoCanoas/WebGIS Empreender e **659 setores do Censo 2022** com atributos populacionais. O contorno do mapa é a união dos bairros, explicitamente identificado como derivado e sem homologação como limite municipal.

## Funcionalidades disponíveis

- Dez páginas: Painel Geral, Mapa de Transporte, Linhas e Itinerários, Pontos de Parada, Monitoramento, Auditoria Operacional, Indicadores, Análise Territorial, Relatórios e Dados e Metodologia.
- Consulta por data e linha, busca por código/nome, sentidos e saídas programadas, identificação da madrugada seguinte e itinerários textuais originais.
- Mapa PMTiles local de bairros e setores, com modo compatível sem WebGL e MapLibre selecionável; densidade, seleção de bairros, popups, localização mediante permissão e fallback GeoJSON. Seleção de várias linhas, desenho e enquadramento quando existe geometria real; hoje 0/81 percursos disponíveis, com indicação explícita. Importador GeoJSON/GTFS com proveniência, escopo municipal e histórico local.
- Temas claro/escuro, menu lateral no desktop e menu móvel com página ativa visível.
- Indicadores de programação, distribuição horária, comparações por data e ranking de saídas por linha, com fórmulas e limites explícitos.
- Relatórios filtrados por data, linha, sentido e horas de serviço; CSV/JSON; impressão para PDF; bases GeoJSON locais.
- Estados honestos de indisponibilidade de GPS, paradas, ETA e trajetos; sem “zero em operação” quando a fonte não está homologada.
- Pipeline Python modular, cache, limite global de tráfego, retry/backoff, validação de esquema, coleta incremental e histórico de publicações em SQLite.
- API FastAPI, persistência operacional SQLite/PostgreSQL, worker controlado, painel privado e revisão imutável de ocorrências. Código testado; **infraestrutura municipal ainda não implantada**.
- CI/CD e coleta estática diária no GitHub Actions. GPS contínuo pertence ao worker externo, não ao Actions.

## Engenharia reversa: o que foi e o que não foi validado

O aplicativo `com.tacom.canoas.gobus` foi identificado na loja TACOM; versão 1.31.3 observada no HTML obtido nesta execução. A documentação de terceiros da família SIU foi investigada. Uma resposta BHZ foi validada como **Belo Horizonte** e excluída de Canoas. O código `GOBUS` mencionado nessa referência não foi considerado confirmação de API municipal.

**Engenharia reversa do APK 1.29.1.2 e validação de serviços em 30/10/2026:** confirmado Cordova, host `mpa.siumobile.com.br:6060` (HTTP legado), rotinas JSONP de linhas, cidades, paradas geográficas, itinerários, veículos e previsões. Em sondagens GET autorizadas de leitura, o host respondeu e o catálogo geral apresentou **1.070 registros da praça MPA** de **14 códigos de município**. O serviço `V3/cidadesLinhas/MPA` identificou **Canoas como `codcid=4`**. Filtragem por esse código resultou em **204 registros de linhas TACOM**; **72 registros** tinham `sgl` coincidente com o catálogo Sogal/NGS de 81 IDs (apenas candidaturas ao cruzamento). Na amostra de uma linha com código `05006`, foram retornadas **64 paradas georreferenciadas** coerentes com o envelope de Canoas e **7 previsões** para uma parada consultada. O itinerário completo não foi obtido nessa amostra porque a previsão não trouxe relação ativa da linha selecionada.

**Escopo desta versão:** os dados TACOM obtidos em testes pontuais **não foram publicados** como cartografia oficial, GPS ou ETA no frontend. O mapa PMTiles mantém **0 percursos e 0 paradas importados** até revisão de codificação, direção, variantes, vigência e condições de redistribuição. Scripts de consulta controlada, validação `MPA/codcid=4`, staging offline, importadores de trajetos/paradas e testes estão no repositório. [Relatório de homologação TACOM](docs/GOBUS-HOMOLOGACAO.md) · [Análise do APK](docs/APK-GOBUS-1.29.1.2.md).

**Ainda pendente:** vínculo SIU→NGS homologado para itinerários e sentidos, geometria de linha completa, cobertura e atualização das paradas, canal HTTPS e limites do fornecedor, timestamp original e contrato de GPS. A obtenção de uma resposta de API de leitura não autoriza concluir que a telemetria esteja apta à auditoria operacional.

A integração real desta versão usa **Sogal/NGS**, cujo portal expõe cadastro, datas, horários e logradouros sem autenticação nas consultas observadas. Catálogo de [endpoints e contratos](docs/ENDPOINTS.md). Google Play, Apple, Sogal e NGS são fontes primárias; a referência SIU de Bruno Armanelli é atribuída e não foi copiada.

## Arquitetura e tecnologias

- Frontend: React 19, TypeScript, Vite, MapLibre GL JS, Leaflet/Canvas, PMTiles v3/MVT, ECharts e CSS responsivo. CSS próprio preserva identidade institucional e reduz a camada de dependências; Tailwind não foi necessário.
- ETL: Python 3.12, cliente HTTP auditável, Shapely e PyProj. EPSG:4326 para intercâmbio, EPSG:31982 para área/distância.
- Histórico: SQLite para snapshots estáticos e testes; PostgreSQL para produção operacional. Modelo PostGIS temporal complementar preparado para geometrias e viagens.
- Backend: FastAPI com API pública de posições recentes e API/painel restritos. Nenhuma chave no frontend. Feed GPS de entrada é um contrato normalizado próprio, dependente de adaptador TACOM homologado.
- Deploy: frontend estático no GitHub Pages; API/worker/banco separados, com Docker Compose e exemplo de proxy TLS.

Fluxo: fonte validada → adaptador → cache/validação → histórico e evidências → produtos públicos → build/testes → Pages. GPS e evidências restritas permanecem no ambiente operacional; não no repositório público.

## Desenvolvimento e testes

```bash
npm ci
python -m venv .venv
.venv/bin/pip install -r requirements.lock
npm run dev
```

```bash
npm run lint
npm test
npm run build
PYTHONPATH=pipeline .venv/bin/pytest -q
PYTHONPATH=pipeline .venv/bin/python scripts/validate_public.py
```

Na base anterior foram aprovados **65 testes Python e 23 testes TypeScript/React**. Novas rotinas de TACOM e testes foram acrescentados; o resultado da revisão corrente deve ser conferido na execução correspondente do [GitHub Actions](https://github.com/marcianolima/webgis-transporte-canoas/actions). Testes abrangem JSON/JSONP, legado, horários/madrugada, contratos NGS com amostras reais, projeção, coordenadas, anomalias, cache/retry, escopo municipal, deduplicação, histórico, autenticação, exportação, navegação e filtros. Consulte a [homologação](docs/HOMOLOGACAO.md) para limites dos testes visuais e da infraestrutura.

## Atualização dos dados e publicação

```bash
PYTHONPATH=pipeline .venv/bin/python -m transporte.collect --days 5
python scripts/prepare_catalogue.py
PYTHONPATH=pipeline .venv/bin/python scripts/validate_public.py
npm run build
```

A coleta usa até duas conexões, intervalo global padrão de 0,75 s, cache e backoff. O cadastro da fonte é consultado por data, sem adivinhação de IDs. Falhas são registradas; falha total preserva a última publicação válida.

O workflow `ci-pages.yml` testa e publica pushes na `main`; atualização estática diária prevista para **05h20 em Brasília**, sujeita à fila do Actions. Permite execução manual com atualização. **Settings → Pages → Source: GitHub Actions** deve estar habilitado. O histórico no cache/artefatos do Actions não substitui backup e disco persistente municipal.

A situação efetivamente observada do deploy está no [relatório](docs/HOMOLOGACAO.md). Build local não é prova de publicação. Para operar API e worker, seguir [Operação](docs/OPERACAO.md); `.env.example` contém apenas nomes e valores vazios/exemplos.

## Estrutura

| Diretório | Conteúdo |
| --- | --- |
| `src/` | Aplicação e testes React/TypeScript |
| `public/data/` | Snapshots e bases públicas, sem fixtures sintéticas |
| `pipeline/transporte/` | HTTP, parsers, NGS, coleta, geoprocessamento, auditoria, store e worker |
| `backend/` | API e painel autenticado de consulta/revisão |
| `infra/` | Dockerfile, modelo PostGIS, proxy e backup |
| `research/` | Evidências sanitizadas e hashes das verificações |
| `tests/` | Testes Python e amostras NGS identificadas |
| `scripts/` | Validação pública, catálogo, cartografia e triagem de APK |
| `docs/` | Contratos, métodos, modelo, operação e relatório |
| `.github/workflows/` | Testes, atualização estática e Pages |
| `var/` | Cache e banco locais; ignorados pelo Git |

## Auditoria e governança

O motor diferencia sinais prováveis e inconclusivos, com evidências e versão do algoritmo. Não emite infrações confirmadas. Saltos, conflitos GPS, lacunas e movimentos interrompidos são testes de consistência; afastamento de trajeto exige geometria homologada. Ausência de GPS **não comprova cancelamento**. Pontualidade, viagens efetivamente realizadas, comboios, map matching, ETA, oferta real por bairro e cobertura populacional permanecem pendentes.

A API/painel administrativo exige chave privada, falha fechada sem configuração e não é servido pelo Pages. TLS e restrição de rede são necessários em produção. A identidade técnica compartilhada deve ser substituída por SSO nominal no uso multiusuário. Não há dados de passageiros, condutores, cartões ou placas inferidas. Não há envio automático de mensagens a terceiros.

Documentação: [Modelo](docs/MODELO-DADOS.md), [Metodologia](docs/METODOLOGIA.md), [Operação e recuperação](docs/OPERACAO.md). Retenção e descarte devem ser definidos no ambiente municipal; o projeto não apaga evidências automaticamente.

## Licenças e créditos

Código original: licença MIT, em `LICENSE`. Dados e serviços permanecem sujeitos aos direitos, condições e atribuições das respectivas fontes. Crédito: Prefeitura de Canoas/GeoCanoas (bairros), IBGE (Censo 2022), Sogal/NGS (programação), TACOM (aplicativos investigados) e OpenStreetMap contributors (fundo opcional, ODbL). A licença MIT não relicencia esses dados ou sistemas. Não é redistribuído APK, código decompilado ou chave de terceiros.

## Histórico

- **0.2.0 — 30/10/2026:** PMTiles local, mapa compatível sem WebGL, seleção e desenho condicionado a geometria real, importador GeoJSON/GTFS, recuperação e testes adicionais.
- **0.1.0 — 30/10/2026:** primeira integração verificável de programação NGS, bairros e setores; frontend público, histórico estático, API/painel privados preparados, motor de consistência, testes e workflow. GPS e demais dependências identificadas explicitamente.

## Revisão 0.2.0

Mapa compatível com navegadores sem WebGL, arquivo PMTiles local com manifesto e hashes, seleção de linhas e bairro, mapa na ficha da linha, importação validada de GeoJSON/GTFS e testes de transporte Range, geometrias e tiles. Engenharia reversa **estática do GoBus/TACOM agora confirmou os contratos no APK**, mas continua sem API GPS municipal homologada; a integração real de horários é Sogal/NGS. Consulte os critérios em [VERSAO-1.0.md](docs/VERSAO-1.0.md).
