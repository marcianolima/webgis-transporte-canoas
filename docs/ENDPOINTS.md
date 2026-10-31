# Catálogo de endpoints

## Sogal / NGS: recursos homologados por resposta e esquema

Base: `https://ngsservicos.com/aplicativos/NgPortais/sogal/scripts/`. Método **GET**, HTTPS, sem credenciais nas consultas observadas. Respostas são arrays JSON com BOM UTF-8. Não há documentação de SLA ou frequência de atualização de origem. Coleta diária, cache e proveniência por resposta.

| Recurso | Parâmetros | Esquema observado | Estado |
| --- | --- | --- | --- |
| `getDataLiberada.php` | nenhum | `[{DATA: YYYY-MM-DD, DIA: string}]` | Homologado |
| `getLinhas.php` | `DATA` | `[{LINHA: string, NOME_COMPLETO: string}]` | Homologado; sem DATA retornou lista vazia |
| `getEspHorario.php` | `LINHA`, `DATA` | `[{LINHA,NOME_COMPLETO,SENTIDO,SENTIDO_2,HRS_BC:[{HR_IV,APD}],HRS_CB:[{HR_IV,APD}]}]` | Homologado |
| `getItinerario.php` | `LINHA` | `[{CIDADE,ORDEM,TP_LOG,NOME_LOG}]` | Homologado para texto, sem coordenadas |

Exemplo mínimo, recortado da resposta de 30/10/2026 para 05000:

```json
{"LINHA":"05000","NOME_COMPLETO":"MATHIAS VELHO / CENTRO","SENTIDO":"Bairro/Centro","HRS_BC":[{"HR_IV":"05:30","APD":"F"}]}
```

`APD` é preservado como atributo de origem; sua semântica não foi homologada e não é convertido em indicador de acessibilidade. `00:00` ao final da sequência após 23h vira minuto de serviço 1440, sem alterar o texto original. Sentido e ordem são preservados conforme a fonte. A sequência textual de logradouros não especifica variantes/sentidos: não é convertida em shape ou sequência de paradas.

Erros: 401/403/404 não geram repetição; 5xx/timeouts têm backoff. HTTP 200 com contrato inválido é falha, não sucesso. Lista vazia de horários é diferente de falha: nenhum registro publicado para o recorte; não implica ausência de serviço ou viagem cancelada.

## Recurso NGS sem homologação geográfica

`https://ngsservicos.com/sogal/scripts/getMapaJson.php?LINHA=05000&SENTIDO=01`: GET, 404 observado nesta sessão. `01` foi extraído do mapeamento Bairro/Centro no bundle do portal. Sem payload de geometria validado.

## Família SIU

Consultar `ENGENHARIA-REVERSA.md` para a pesquisa histórica da família SIU. **Nesta revisão foram confirmados em MPA os serviços de leitura de cidades, linhas, paradas e previsões com amostras de Canoas.** Isso não constitui homologação da telemetria GPS ou de todos os itinerários. JSONP é analisado como dados, nunca executado. O parser admite listas de dicionários em string legada com `ast.literal_eval`, sem `eval` e sem substituir apóstrofos de nomes.

## GoBus/TACOM — contratos confirmados estaticamente no APK 1.29.1.2

A análise do APK confirmou o host configurado `http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/` e caminhos de GET/JSONP para `buscarLinhas`, `cidadesApp`, `V3/buscarItinerario`, `V3/retornaVeiculosMapa`, `V3/buscarParadasPorLinhaComCoordenadas`, `V3/buscarPrevisoes`, `V3/retornaQroLinha` e outros. Contratos e campos: [relatório da análise do APK](APK-GOBUS-1.29.1.2.md).

**Resultados operacionais observados, sem publicação automática:** `cidadesApp` retornou lista de cidades vazia; `buscarLinhas` retornou 1.070 registros da praça MPA; `V3/cidadesLinhas/MPA/retornoJSONCidadesLinhas` confirmou a relação `CANOAS → codcid 4`. O filtro `praca=MPA` e `codcid=4` identificou 204 linhas TACOM. Destas, 72 registros apresentaram código `sgl` exato candidato ao catálogo NGS de 81 IDs. Uma linha de teste, `05006`, retornou 64 paradas georreferenciadas coerentes com a região e sete previsões consultadas em uma parada, mas não confirmou ID de itinerário ativo para essa linha.

Consultas e normalização ficam nos scripts de sondagem de catálogo e geografia; relatórios e controles em [GOBUS-HOMOLOGACAO.md](GOBUS-HOMOLOGACAO.md). **Trajetos completos, GPS, ETA em produção e redistribuição ao público permanecem pendentes de validação.** As URLs legadas são HTTP, portanto não devem transportar credenciais ou alimentar diretamente a aplicação pública.

Geometria de itinerário: `coordX`=longitude, `coordY`=latitude, em ordem; conversão para GeoJSON LineString não certifica vínculo entre os IDs SIU e os códigos NGS do catálogo atual. A telemetria vista pelo cliente não comprova timestamp GPS de origem. O backend operacional e os arquivos PMTiles continuam sujeitos a homologação separada.

## Backend próprio

| Endpoint | Acesso | Finalidade |
| --- | --- | --- |
| `GET /v1/health` | Público | Último resultado da coleta, sem erro ou URL sensível |
| `GET /v1/vehicles` | Público | Campos públicos, posições até 180 s e fonte homologada |
| `GET /admin` | Basic `admin` + chave | Painel de consulta e revisão municipal |
| `GET /internal/positions` | Basic ou Bearer | Filtros start/end com fuso, vehicle, route, limite e truncamento explícito |
| `GET /internal/events` | Basic ou Bearer | Ocorrências com evidências, até 1000 por recorte |
| `GET /internal/export` | Basic ou Bearer | CSV e GeoJSON, máximo de 50 mil posições, intervalo de até 7 dias |
| `POST /internal/events/{id}/reviews` | Basic ou Bearer | Revisão imutável, classificação e fundamentação, autor técnico de credencial compartilhada |

A chave é somente do servidor (`ADMIN_API_KEY`, mínimo de 32 caracteres). A configuração ausente falha de forma fechada. Produção exige TLS. O painel público não solicita nem recebe a chave. A identidade compartilhada não equivale a identificação nominal; integrar SSO municipal antes de uso multiusuário com responsabilização individual.

Feed de entrada do worker: contrato **normalizado próprio**, não uma alegação de compatibilidade direta com SIU. Exige `{vehicles:[{source_id,vehicle_id,route_id,observed_at,longitude,latitude,scope:"municipal",municipality_code:"4304606",speed_kmh?,bearing?}]}`. Registros de outras redes são rejeitados. Adaptador do protocolo efetivo da TACOM depende da validação do APK e amostras.

## Arquivos cartográficos da aplicação — 0.2.0

`data/transporte-canoas.pmtiles`: arquivo PMTiles v3/MVT estático publicado no Pages. Leitura GET/Range; alternativa GET completo limitada a 20 MB para servidor sem Range. `data/map-manifest.json`: tamanho, SHA-256, fontes, contagens e disponibilidade por linha. `data/route-shapes.geojson`: geometrias de referência com proveniência, atualmente FeatureCollection vazia com status pendente. Estes arquivos são produtos locais; não são endpoints descobertos do GoBus.
