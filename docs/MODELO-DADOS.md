# Modelo de dados, histórico e reprocessamento

## Publicação estática

- `network.json`: versão do esquema, datas consultadas, situação da coleta, linhas, saídas, logradouros e erros. Chave de linha é string: preserva zeros no ID da origem.
- Cada saída registra linha, data de serviço, sentido original, sequência, horário, minuto de serviço, origem, hora de obtenção e SHA-256 da resposta.
- Itinerário textual tem proveniência própria; não é associado a sentido por suposição.
- `catalogue.json`: fontes e métodos com situação explícita.
- `territory.json`: área calculada em EPSG:31982, atributos populacionais de referência e resultados disponíveis por bairro. Valores indisponíveis são `null`.
- `vehicles.json`: vazio com situação indisponível até homologação; não contém fixtures.
- GeoJSON local: bairros, setores, paradas (vazio quando indisponíveis), contorno derivado da união de bairros.

## Histórico estático

`var/static-history.sqlite` tem `snapshot(kind,natural_key,hash,observed_at,payload)` e `run(started_at,ended_at,status,errors)`. Deduplicação por chave e hash do conteúdo estável, sem timestamp de obtenção no hash. Preserva mudanças de programação e cadastro. Não prova o intervalo oficial de vigência: é histórico de **observação de publicações**. As datas incluídas no snapshot fazem parte do conteúdo e podem produzir uma nova versão diária do cadastro.

Respostas originais são cacheadas por SHA-256 da URL em `var/cache`. Cada entrada preserva URL, obtenção, HTTP, SHA-256 do corpo e corpo. O pipeline não armazena credenciais nessa fonte pública. O relatório `research/collection-evidence.json` lista resultados e hashes sem repetir corpos.

## Histórico operacional

A implementação de `transporte.store` suporta SQLite (desenvolvimento/testes) e PostgreSQL (produção):

| Tabela | Conteúdo e invariantes |
| --- | --- |
| `position` | fonte, veículo, linha, observação UTC, obtenção UTC, coordenadas, velocidade/direção opcionais, payload; imutável |
| `collection_run` | execução, início/fim, aceitos/rejeitados, situação e classe sanitizada de erro |
| `audit_event` | regra, versão do algoritmo, classificação, fonte/veículo/linha, instante e evidências |
| `audit_review` | revisão acrescentada sem substituir a evidência, autor da credencial e fundamentação |

Deduplicação: hash de fonte + veículo + instante de origem + coordenadas. Coordenadas diferentes no mesmo instante são mantidas para evidência; consulta atual escolhe deterministicamente um único registro por veículo/fonte. O motor sinaliza conflito como inconclusivo. Índices por veículo/fonte/tempo e linha/tempo. Timestamps normalizados em UTC com fuso explícito; interface exibe America/Sao_Paulo.

## Modelo PostGIS complementar

`infra/sql/001_model.sql` cria fonte, linha temporal, versão de itinerário, parada temporal, sequência de paradas, viagem programada, viagem observada e indicador. Há geometrias 4326 e índices GiST. São estruturas **preparadas**, ainda sem importadores de viagens/shapes homologados. O worker atual grava somente as quatro tabelas operacionais acima.

Não há alegação de particionamento ou map matching implementados. Planejar particionamento mensal e índice BRIN quando o volume real justificar. `CREATE TABLE IF NOT EXISTS` suporta a primeira implantação; mudanças futuras de esquema precisam de migrações versionadas próprias.

## Reprocessamento

Os eventos incluem algoritmo `audit-0.1.0` e evidências. `Store.save_events(Store.history(...))` reprocessa um recorte sem duplicar eventos idênticos. Nova versão do algoritmo gera novo hash e preserva o resultado antigo. Revisões permanecem associadas ao ID do evento original. Para reanálise geográfica, fornecer a versão temporal homologada do shape a `trajectory_events`; o worker ainda não possui essa associação e não executa a regra de afastamento em produção.
