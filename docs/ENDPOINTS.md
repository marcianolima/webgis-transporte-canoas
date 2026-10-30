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

Consultar `ENGENHARIA-REVERSA.md`. Somente contrato de BHZ observado; **nenhum endpoint SIU homologado para Canoas**. JSONP é analisado como dados, nunca executado. O parser admite listas de dicionários em string legada com `ast.literal_eval`, sem `eval` e sem substituir apóstrofos de nomes.

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
