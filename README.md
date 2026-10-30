# WebGIS Transporte Canoas

Plataforma de informação e análise do transporte coletivo municipal de Canoas/RS, com programação real da Sogal, cartografia local, metodologia aberta e infraestrutura para histórico e fiscalização.

**Versão 0.1.0 — programação e território integrados; GPS GoBus ainda não homologado.** Não é declarado atendimento integral dos critérios da versão 1.0. Não são gerados veículos, paradas, viagens realizadas ou infrações fictícios.

[Aplicação pública](https://marcianolima.github.io/webgis-transporte-canoas/) · [Execuções e deploy](https://github.com/marcianolima/webgis-transporte-canoas/actions) · [Relatório técnico](docs/HOMOLOGACAO.md)

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
- Mapa de bairros e setores; densidade populacional; zoom, seleção e popups; localização do usuário somente mediante permissão. MapLibre com alternativa Leaflet quando WebGL está indisponível.
- Temas claro/escuro, menu lateral no desktop e menu móvel com página ativa visível.
- Indicadores de programação, distribuição horária, comparações por data e ranking de saídas por linha, com fórmulas e limites explícitos.
- Relatórios filtrados por data, linha, sentido e horas de serviço; CSV/JSON; impressão para PDF; bases GeoJSON locais.
- Estados honestos de indisponibilidade de GPS, paradas, ETA e trajetos; sem “zero em operação” quando a fonte não está homologada.
- Pipeline Python modular, cache, limite global de tráfego, retry/backoff, validação de esquema, coleta incremental e histórico de publicações em SQLite.
- API FastAPI, persistência operacional SQLite/PostgreSQL, worker controlado, painel privado e revisão imutável de ocorrências. Código testado; **infraestrutura municipal ainda não implantada**.
- CI/CD e coleta estática diária no GitHub Actions. GPS contínuo pertence ao worker externo, não ao Actions.

## Engenharia reversa: o que foi e o que não foi validado

O aplicativo `com.tacom.canoas.gobus` foi identificado na loja TACOM; versão 1.31.3 observada no HTML obtido nesta execução. A documentação de terceiros da família SIU foi investigada. Uma resposta BHZ foi validada como **Belo Horizonte** e excluída de Canoas. O código `GOBUS` mencionado nessa referência não foi considerado confirmação de API municipal.

Nenhum APK autorizado estava disponível. Nenhuma decompilação, captura de tráfego ou endpoint GPS municipal foi homologado. Hosts candidatos retornaram 503 neste ambiente; uma consulta SIU com praça GOBUS retornou lista vazia, insuficiente para homologação. O endpoint de mapa NGS retornou 404. As descobertas, hipóteses e bloqueios estão em [Engenharia reversa](docs/ENGENHARIA-REVERSA.md), com utilitário offline de triagem de APK.

A integração real desta versão usa **Sogal/NGS**, cujo portal expõe cadastro, datas, horários e logradouros sem autenticação nas consultas observadas. Catálogo de [endpoints e contratos](docs/ENDPOINTS.md). Google Play, Apple, Sogal e NGS são fontes primárias; a referência SIU de Bruno Armanelli é atribuída e não foi copiada.

## Arquitetura e tecnologias

- Frontend: React 19, TypeScript, Vite, MapLibre GL JS, Leaflet, ECharts e CSS responsivo. CSS próprio preserva identidade institucional e reduz a camada de dependências; Tailwind não foi necessário.
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

Resultado local: **55 testes Python e 10 testes TypeScript/React aprovados**, lint e build de produção aprovados. Testes abrangem JSON/JSONP, legado, horários/madrugada, contratos NGS com amostras reais, projeção, coordenadas, anomalias, cache/retry, escopo municipal, deduplicação, histórico, autenticação, exportação, navegação e filtros. Consulte a [homologação](docs/HOMOLOGACAO.md) para limites dos testes visuais e da infraestrutura.

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

- **0.1.0 — 30/10/2026:** primeira integração verificável de programação NGS, bairros e setores; frontend público, histórico estático, API/painel privados preparados, motor de consistência, testes e workflow. GPS e demais dependências identificadas explicitamente.
