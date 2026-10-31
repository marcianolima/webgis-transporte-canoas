# Integração autorizada GoBus/TACOM — homologação

Situação: engenharia reversa estática do APK 1.29.1.2 concluída; os contratos de leitura estão mapeados. **Dados de produção ainda não homologados para Canoas.** Não se devem confundir IDs do SIU Mobile com os IDs de linha do NGS/Sogal.

## Componentes entregues

| Recurso | Arquivo | Papel |
| --- | --- | --- |
| Parser JSONP e contratos | `pipeline/transporte/gobus.py` | Leitura segura de linhas, cidades, paradas, itinerários, previsões e veículos |
| Sonda de metadados | `scripts/gobus_probe_catalogue.py` | Até 2 GET, cidade e linhas; resume quantidade; não coleta GPS |
| Workflow de sondagem | `.github/workflows/gobus-probe.yml` | Sonda de execução única no push de criação/alteração de workflow, e execução manual |
| Captura cartográfica | `scripts/gobus_capture_geography.py` | Até 12 GET geográficos por execução, com pausa de 3 segundos e validação prévia CAN |
| Preparação cartográfica | `pipeline/transporte/gobus_staging.py` | Vincula capturas SIU→NGS sob aprovação explícita e produz GeoJSON de revisão |
| Importação oficial do WebGIS | `pipeline/transporte/import_shapes.py` | Publica geometrias homologadas mediante fonte HTTPS explícita e reconstrói PMTiles |
| Testes | `tests/test_gobus.py` e `tests/test_gobus_staging.py` | Cobertura de parsing, formatos, limites, escopo, autorização, compatibilidade territorial |

## 1. Sonda de catálogo

O APK configura a origem legada `http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/`, que **não usa TLS**. Não inserir credenciais nessa URL. Se a TACOM fornecer origem HTTPS ou ambiente homologado, adaptar com validação explícita da origem e redirecionamentos proibidos. A sonda inicial limita o tráfego a:

- GET `cidadesApp/retornoJSONCidades`
- GET `buscarLinhas/retornoJSONListaLinhas`

Uma tentativa autorizada via GitHub Actions foi programada; conferir [execuções](https://github.com/marcianolima/webgis-transporte-canoas/actions/workflows/gobus-probe.yml). O sucesso de um HTTP 200 não basta: exigir a identificação oficial CAN/Canoas, que precisa ocorrer na resposta do fornecedor. O endpoint de linhas do APK não está necessariamente filtrado pelo município.

Execução por operador autorizado em rede de confiança:

```bash
PYTHONPATH=pipeline python scripts/gobus_probe_catalogue.py --autorizado --aceito-http
```

O comando reporta apenas estatísticas. Não grava o corpo em repositório público. Para validar uma resposta individual, use `scripts/verify_gobus_endpoint.py`, que salva o resultado no diretório ignorado `var/gobus/`.

## 2. Captura geográfica limitada

Somente após confirmar CAN/Canoas e os IDs reais do fornecedor, copie e edite `examples/gobus-capture-plan.example.json`. Defina `authorized=true` e `allow_plain_http=true` **após avaliação da rede e da autorização aplicável**. Substitua os IDs de exemplo pelos IDs obtidos da TACOM.

```bash
PYTHONPATH=pipeline python scripts/gobus_capture_geography.py \
  caminho/para/plano-revisado.json \
  --output var/gobus/captures
```

Cada execução faz a verificação de cidade e no máximo 12 leituras de paradas por linha ou geometrias de itinerário, com pausa de 3 segundos. Não são feitas enumerações de IDs, tentativas de login, scraping de cartões, coleta de alarmes ou leituras GPS. Os JSONP de origem, um manifesto com SHA-256 e a data UTC da captura permanecem fora do GitHub Pages.

O identificador de itinerário não pode ser derivado diretamente de todo `codLinha` ou do quadro textual de horários. Pode aparecer em `buscarPrevisoes` de uma parada atendida, **mas apenas para veículos que naquele momento possuem previsão**, e pode variar com serviço/dia. Para cobertura total das variantes, solicitar à TACOM uma tabela oficial de **linha ↔ sublinha ↔ sentido ↔ itinerário ↔ validade**; não adivinhar IDs por enumeração.

## 3. Correspondência entre bases

Use `examples/gobus-staging-manifest.example.json` como modelo. Exige:

1. `city_confirmed=true` mediante resposta da TACOM com `CAN` / Canoas.
2. `authorization_confirmed=true` após controle de acesso e direito de uso.
3. Cada `siu_line_id` precisa existir na captura `buscarLinhas`; cada `ngs_route_id` precisa existir no `public/data/network.json`.
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
- Paradas precisam passar por validação, deduplicação e publicação geográfica controlada; o staging **não altera** `public/data/stops.geojson`.
- GPS e ETA exigem serviço municipal estável, identificação não ambígua de veículo/linha, atributos e limites de atualização. A API de mapa do GoBus não apresenta timestamp GPS de origem comprovado no cliente 1.29.1.2; o horário da consulta não é hora da leitura embarcada.
- Para auditoria de pontualidade, viagens realizadas e desvios é imprescindível histórico temporal confiável, correspondência de viagem/itinerário e critérios técnicos. **Não promover posições instantâneas não temporalizadas a infrações ou cumprimento de viagem.**

## Critérios objetivos de aceite

A integração só será classificada como homologada depois de: (a) acesso e protocolo autorizados confirmados; (b) cidade Canoas verificada na resposta; (c) ao menos uma linha SIU e sua correspondência NGS revisada; (d) uma geometria real e paradas coerentes aprovadas; (e) autorização de divulgação, origem/versão/hash e data preservados. Monitoramento GPS exigirá, separadamente, campos e periodicidade da observação, estabilidade/limites e disponibilidade do serviço.

**Não colocar respostas JSONP brutas, tokens nem dados operacionais não autorizados no repositório público.** O GitHub Actions faz somente a sondagem de metadados; o capturador permanece para rede/ambiente técnico controlado.
