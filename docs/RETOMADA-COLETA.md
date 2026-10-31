# Retomada segura da coleta — 0.3.1, 31/10/2026

## Resultado observado

Uma nova consulta GET ao catálogo de cidades respondeu **HTTP 200 em 4,92 s**, confirmando Canoas (`codcid=4`, praça `MPA`). O cancelamento de aprovação de rede da tentativa anterior não voltou a ocorrer nesta execução. Não há evidência que permita atribuir aquele cancelamento ao tempo de resposta da TACOM.

Em seguida, uma coleta limitada terminou entre **08h53 e 08h56 em Brasília** (11h53–11h56 UTC): **77 requisições HTTP, 77 respostas válidas, 114 usos de cache, nenhuma falha e nenhuma nova tentativa necessária**. Foram consultadas as listas das 72 linhas com correspondência exata de código municipal, sem filtrar apenas linhas com horário naquele sábado. As listas reuniram 1.433 IDs de parada; isso não significa 1.433 coordenadas recuperadas.

| Produto | Publicação anterior | Publicação mesclada |
| --- | ---: | ---: |
| Itinerários de referência | 52 | 57 |
| Linhas com geometria | 35 | 36 |
| Paradas geográficas | 215 | 385 |
| Percursos sob revisão de borda | 7 | 8 |
| PMTiles, bytes | 479.399 | 541.915 |

A captura nova isolada tinha 56 itinerários e 376 paradas. A mesclagem conservou um itinerário e nove paradas ausentes dessa captura: uma amostra sem previsões não comprova remoção. **Todos os 52 itinerários, as 215 paradas e os 602 vínculos parada–linha anteriores foram preservados.** A publicação ganhou cinco itinerários e 170 paradas. A linha `05116` passou a ter geometria. Os novos IDs observados foram `SIU-2457`, `SIU-2473`, `SIU-2487`, `SIU-3019` e `SIU-3143`; nenhum ID foi adivinhado.

PMTiles v3/MVT, 28 tiles, 18 bairros, 659 setores, um contorno derivado, 57 itinerários e 385 paradas. SHA-256: `839b79cea602df391b3f96246680b8b7ced7a9310916d857edb30224711d4df3`.

## O que aumentar a espera resolve

O leitor agora permite `--timeout 60` (padrão; faixa de 10 a 90 segundos) e `--retries 2` (até duas novas tentativas). Esse timeout é o timeout de operações do socket; não é um prazo total garantido da coleta. A espera maior pode ajudar em respostas lentas. **Não altera decisões de autorização da rede, autenticação ou permissões de um aplicativo.**

Novas tentativas ocorrem somente em erros transitórios, com backoff, e consomem o mesmo orçamento total de requisições. HTTP 401/403 suspende novas consultas, sem tentar contornar o bloqueio. HTTP 429 respeita a espera indicada; esperas acima de 30 segundos suspendem a execução para retomada posterior. Três recursos consecutivos com falhas transitórias esgotadas suspendem novas requisições. Mantidos até dois leitores concorrentes e intervalo global mínimo de 1,5 s (comando usado: 2 s).

## Retomada e preservação

1. Antes da consulta real, foi criado um checkpoint privado de **212 arquivos, 7.252.404 bytes**, com hashes, incluindo capturas, cache e produtos publicados. A comparação posterior confirmou a conservação de todas as 135 capturas brutas anteriores (212 capturas distintas após a coleta). Uma cópia privada recuperável reuniu 429 arquivos, com CRC e SHA-256 de cada entrada verificados; ela não foi publicada no GitHub. O GitHub permanecia no commit `b12c62fd94fb983453dfc28bbba5e29f63d4a8b2`.
2. Cada resposta válida é arquivada por identidade/hash em `var/gobus/source-history/`. O cache é atualizado por substituição de arquivo completo, depois de validar o JSONP. Timeout, erro de esquema ou gravação incompleta não substitui a captura anterior.
3. A repetição do mesmo comando aproveita o cache válido: 24 h para cadastros/geometrias e 5 min para previsões. Previsões expiradas são consultadas de novo; o histórico anterior permanece. Não remover o diretório para retomar.
4. `var/gobus/runs/` registra progresso por requisição, cache, tentativas, limites e estado final. Se o processo morrer abruptamente, pode restar estado `running`; ele não é prova de sucesso. A retomada depende de conservar o disco privado.
5. O publicador rejeita capturas incompletas com datas de geração divergentes, mescla IDs sem inferir remoções e conserva vínculos e sentidos já observados. Identidade de itinerário conflitante ou mudança de coordenada da mesma parada exige revisão; não é aplicada silenciosamente.
6. Toda a preparação territorial e o PMTiles são construídos em diretório temporário isolado. Só depois os produtos completos são promovidos. Erro tratado durante promoção restaura os arquivos anteriores. `var/gobus/publication-runs/` conserva journal e cópia dos arquivos substituídos. Há trava para evitar dois publicadores simultâneos.
7. A substituição é atômica por arquivo; não equivale a uma transação entre todos os arquivos durante queda de energia ou encerramento forçado. Nesse caso, revisar o journal `prepared`, restaurar os arquivos de `before/` (e remover os que não existiam) ou refazer a publicação validada antes do deploy. O Pages somente recebe o build aprovado inteiro.

Comando executado (somente consultas informativas autorizadas):

```bash
PYTHONPATH=pipeline .venv/bin/python -m transporte.gobus_geography \
  --authorized --allow-plain-http --max-requests 180 \
  --geo-samples 32 --prediction-samples 16 --interval 2 \
  --timeout 60 --retries 2
PYTHONPATH=pipeline .venv/bin/python -m transporte.publish_geography
PYTHONPATH=pipeline .venv/bin/python scripts/prepare_catalogue.py
PYTHONPATH=pipeline .venv/bin/python scripts/validate_public.py
```

No GitHub, `refresh_geography=true` continua sendo uma opção **manual**, desligada por padrão; usa timeout de 60 s e duas novas tentativas. Os produtos normalizados existentes no checkout são mesclados. Capturas TACOM privadas não são expostas em cache ou artefatos públicos. Cada runner é efêmero: retomada das capturas brutas entre runs exige worker com disco privado persistente; o histórico público normalizado continua versionado no Git. O agendamento diário é da programação NGS, sem coleta GPS contínua.

## Limitações mantidas

Restam **45 de 81 linhas** do catálogo NGS sem geometria publicada. As 385 paradas são uma amostra das listas consultadas. Oito percursos têm sinalização de borda para revisão; a união dos bairros não é limite municipal homologado. As geometrias conservam fonte, hash, hora e estado de referência; ausência de previsão não altera sua vigência nem comprova operação. Não há homologação de sentidos, variantes, equivalência aos horários, GPS contínuo ou ETA público.

A origem continua HTTP legado, sem autenticação TLS da integridade da resposta. Não houve captura de tráfego privado nem contorno de autenticação. JSONP bruto e identificadores de veículos permanecem privados. [Pendências da versão 1.0](VERSAO-1.0.md).

## Validação

Testes cobrem timeout, limite de tentativas, retomada por cache, preservação após erro, gravação atômica, suspensão em 403/429/falhas repetidas, preservação de vínculos, rejeição de captura incompleta e rollback da publicação. Os resultados locais e remotos desta revisão são registrados em [HOMOLOGACAO.md](HOMOLOGACAO.md) e `research/network-retry-2026-10-31.json`.
