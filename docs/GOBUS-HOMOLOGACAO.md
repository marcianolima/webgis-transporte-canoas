# Integração autorizada GoBus/TACOM — homologação

**Atualização 31/10/2026 / 0.3.0:** geometrias de referência publicadas: 52 itinerários de 35 linhas e 215 paradas. O serviço de coordenadas por linha devolveu Viamão no acesso testado e foi excluído; o novo fluxo usa listas de IDs, consultas de parada individual/proximidade e itinerários observados em previsões municipais. Ver [EVOLUCAO-0.3.md](EVOLUCAO-0.3.md). As seções seguintes preservam o diagnóstico anterior; dados agora publicados continuam sem homologação operacional.


Situação: engenharia reversa estática do APK 1.29.1.2 concluída; os contratos de leitura estão mapeados. **Cadastro de linhas e cartografia de referência disponíveis; GPS e ETA continuam sem homologação para publicação operacional.** Não se devem confundir IDs do SIU Mobile com os IDs de linha do NGS/Sogal.

## Componentes entregues

| Recurso | Arquivo | Papel |
| --- | --- | --- |
| Parser JSONP e contratos | `pipeline/transporte/gobus.py` | Leitura segura de linhas, cidades, paradas, itinerários, previsões e veículos |
| Sonda de metadados | `scripts/gobus_probe_catalogue.py` | Até 2 GET, cidade e linhas; resume quantidade; não coleta GPS |
| Sondas de catálogo | `scripts/gobus_probe_{lines,citylines,canoas_lines}.py` | Validam a praça MPA, município codcid=4 e candidatos ao cruzamento NGS |
| Workflow de sondagem | `.github/workflows/gobus-probe*.yml` | Consultas limitadas, com resultados sanitizados no Actions |
| Captura cartográfica | `scripts/gobus_capture_geography.py` | Até 12 GET geográficos por execução, com pausa de 3 segundos e validação prévia de praça MPA e codcid=4 |
| Crosswalk para revisão | `pipeline/transporte/gobus_crosswalk.py` | Gera CSV de candidatos por códigos exatos sem autoaprovar sentido, variante ou vigência |
| Preparação cartográfica | `pipeline/transporte/gobus_staging.py` | Vincula capturas SIU→NGS sob aprovação explícita e produz GeoJSON de revisão |
| Importação de trajetos | `pipeline/transporte/import_shapes.py` | Publica percursos homologados mediante origem HTTPS e reconstrói PMTiles |
| Importação de paradas | `pipeline/transporte/import_stops.py` | Valida, arquiva e publica pontos de parada mediante aprovação, reconstruindo PMTiles |
| Testes | `tests/test_gobus.py` e `tests/test_gobus_staging.py` | Cobertura de parsing, formatos, limites, escopo, autorização, compatibilidade territorial |

## 1. Sonda de catálogo

O APK configura a origem legada `http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/`, que **não usa TLS**. Não inserir credenciais nessa URL. Se a TACOM fornecer origem HTTPS ou ambiente homologado, adaptar com validação explícita da origem e redirecionamentos proibidos. A sonda inicial limita o tráfego a:

- GET `cidadesApp/retornoJSONCidades`
- GET `buscarLinhas/retornoJSONListaLinhas`

**Resultados reais de 30/10/2026:** o endpoint `cidadesApp` respondeu `sucesso` com a lista `cidade` vazia. Já `buscarLinhas` retornou **1.070 registros** na praça `MPA`, com 14 códigos numéricos de cidade. A chamada `V3/cidadesLinhas/MPA/retornoJSONCidadesLinhas` confirmou **Canoas = `codcid=4`**. Filtrando `praca=MPA` e `codcid=4`, obtivemos **204 registros de linhas TACOM**. Comparando códigos `sgl` normalizados por zeros à esquerda com os 81 IDs NGS do snapshot, **72 registros tiveram correspondência exata candidata**, ainda sem homologar sentido, vigência, variantes ou equivalência operacional. As execuções são públicas em [GitHub Actions](https://github.com/marcianolima/webgis-transporte-canoas/actions). Nenhuma resposta GPS foi coletada nessas sondagens.

**Importante:** não condicionar o escopo municipal à presença de `CAN` em `cidadesApp` quando a fonte real utiliza a praça **MPA** e a tabela `cidadesLinhas` para mapear o `codcid`. O código numérico foi observado diretamente e não foi adivinhado.
Execução por operador autorizado em rede de confiança:

```bash
PYTHONPATH=pipeline python scripts/gobus_probe_catalogue.py --autorizado --aceito-http
```

O comando reporta apenas estatísticas. Não grava o corpo em repositório público. Para validar uma resposta individual, use `scripts/verify_gobus_endpoint.py`, que salva o resultado no diretório ignorado `var/gobus/`.

### Gerar CSV privado de correspondência candidato (revisão manual)

Depois de salvar uma resposta de `V3/cidadesLinhas/MPA/retornoJSONCidadesLinhas` e outra de `buscarLinhas/retornoJSONListaLinhas` na pasta privada `var/gobus/`, gerar:

```bash
PYTHONPATH=pipeline python -m transporte.gobus_crosswalk \
  --cidades var/gobus/cidades-linhas.jsonp \
  --linhas var/gobus/linhas.jsonp \
  --network public/data/network.json \
  --output var/gobus/revisao-crosswalk.csv
```

Os nomes dos arquivos são ilustrativos; utilizar os nomes efetivos das capturas obtidas. O CSV inclui identificador de linha TACOM, código `sgl`, nome, candidato `ngs_route_id` e campos **`crosswalk_approved=false`**, `direction_review=pending`, `variant_review=pending`, `validity_review=pending`. A coincidência exata dos códigos **não aprova itinerários e não justifica inserir linhas no mapa**.

## 2. Captura geográfica limitada

Após a confirmação já realizada de `MPA/codcid=4`, valide os IDs específicos de linha/itinerário com a TACOM; então copie e edite `examples/gobus-capture-plan.example.json`. Defina `authorized=true` e `allow_plain_http=true` **após avaliação da rede e da autorização aplicável**. Substitua os IDs de exemplo pelos IDs obtidos da TACOM.

```bash
PYTHONPATH=pipeline python scripts/gobus_capture_geography.py \
  caminho/para/plano-revisado.json \
  --output var/gobus/captures
```

Cada execução consulta e verifica `cidadesLinhas` e `buscarLinhas`, restringe os IDs a `codcid=4`, e faz no máximo 12 leituras de paradas por linha ou geometrias de itinerário, com pausa de 3 segundos. Não são feitas enumerações de IDs, tentativas de login, scraping de cartões, coleta de alarmes ou leituras GPS. Os JSONP de origem, um manifesto com SHA-256 e a data UTC da captura permanecem fora do GitHub Pages.

O identificador de itinerário não pode ser derivado diretamente de todo `codLinha` ou do quadro textual de horários. Pode aparecer em `buscarPrevisoes` de uma parada atendida, **mas apenas para veículos que naquele momento possuem previsão**, e pode variar com serviço/dia. Para cobertura total das variantes, solicitar à TACOM uma tabela oficial de **linha ↔ sublinha ↔ sentido ↔ itinerário ↔ validade**; não adivinhar IDs por enumeração.

### Diagnóstico adicional: itinerários e sublinhas da linha 05006

A sonda de cinco paradas obteve **37 previsões** e **nenhuma relação de itinerário municipal validável** sob o contrato interpretado. Uma consulta específica `V3/retornaSublinhasDaLinha/{codLinha}/0/MPA/retornoSublinhasJSON` respondeu `sucesso` e `subLinhas=[]`. Esses resultados **não provam inexistência de percursos**; indicam apenas que a associação não está disponível pelas leituras testadas.

**Dependência a solicitar à TACOM:** exportação estática da relação `codLinha → código de sublinha → codItinerario → sentido/variante → vigência`, ou documentação oficial de como recuperá-la. Sem ela não publicar geometrias por associação inferida nem enumerar identificadores de itinerário.

## 3. Correspondência entre bases

Use `examples/gobus-staging-manifest.example.json` como modelo. Exige:

1. `city_confirmed=true` após confirmar no serviço `V3/cidadesLinhas/MPA` a relação `CANOAS` / `cod=4`. Guardar essa resposta em `line_cities_file` e informar `canoas_city_id=4`. A antiga alternativa `cidadesApp` permanece suportada se um serviço futuro apresentar `CAN`.
2. `authorization_confirmed=true` após controle de acesso e direito de uso.
3. Cada `siu_line_id` precisa existir na captura `buscarLinhas`, com `codcid=4` quando a origem for `MPA`; cada `ngs_route_id` precisa existir em `public/data/network.json`.
4. `crosswalk_approved=true` apenas após correspondência validada, **não por semelhança de nomes**.
5. Cada itinerário exige `relation_approved=true`, sentido/variante declarado e vértices geográficos reais.

```bash
PYTHONPATH=pipeline python -m transporte.gobus_staging \
  --manifest caminho/para/manifesto-aprovado.json \
  --source-dir var/gobus/captures \
  --network public/data/network.json \
  --output var/gobus/staging
```

Saídas privadas: `routes.geojson`, `stops.geojson`, `crosswalk.json`, `evidence.json` e `summary.json`. Rotas com latitudes/longitudes externas ao envelope operacional de Canoas, pontos de parada conflitantes e vínculos sem aprovação são rejeitados. O envelope é um teste de coerência, **não a definição legal do perímetro municipal**.

## 4. Publicação cartográfica e monitoramento

Após revisão técnica dos dados, vigência e permissões de redistribuição:

- As rotas homologadas podem passar pelo importador de geometrias do WebGIS com `source-url` HTTPS confiável e `source-name` real. O importador valida linhas existentes, cria histórico e reconstrói PMTiles.
- Paradas têm importador próprio `transporte.import_stops`: valida coordenadas e linhas, exige aprovação e URL de proveniência HTTPS, arquiva histórico por hash, atualiza `public/data/stops.geojson` e reconstrói PMTiles. O staging **não altera** arquivos públicos.
- GPS e ETA exigem serviço municipal estável, identificação não ambígua de veículo/linha, atributos e limites de atualização. A API de mapa do GoBus não apresenta timestamp GPS de origem comprovado no cliente 1.29.1.2; o horário da consulta não é hora da leitura embarcada.
- Para auditoria de pontualidade, viagens realizadas e desvios é imprescindível histórico temporal confiável, correspondência de viagem/itinerário e critérios técnicos. **Não promover posições instantâneas não temporalizadas a infrações ou cumprimento de viagem.**

### Importar pontos de parada já revisados

```bash
PYTHONPATH=pipeline python -m transporte.import_stops var/gobus/staging/stops.geojson \
  --source-url https://ENDPOINT-OFICIAL-HTTPS-VALIDADO/arquivo.geojson \
  --source-name 'TACOM / responsável técnico' \
  --reference-date 2026-10-30 \
  --municipality-code 4304606 \
  --approved
```

O endereço HTTPS é **um parâmetro a substituir por fonte real**; não utilizar URL inventada. Sem origem segura auditável, manter os registros em staging privado.

## Critérios objetivos de aceite

A integração só será classificada como homologada depois de: (a) acesso e protocolo autorizados confirmados; (b) cidade Canoas verificada na resposta; (c) ao menos uma linha SIU e sua correspondência NGS revisada; (d) uma geometria real e paradas coerentes aprovadas; (e) autorização de divulgação, origem/versão/hash e data preservados. Monitoramento GPS exigirá, separadamente, campos e periodicidade da observação, estabilidade/limites e disponibilidade do serviço.

**Não colocar respostas JSONP brutas, tokens nem dados operacionais não autorizados no repositório público.** O GitHub Actions faz somente a sondagem de metadados; o capturador permanece para rede/ambiente técnico controlado.
