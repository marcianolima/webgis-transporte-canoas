# Monitoramento TACOM/GoBus por consulta — integração experimental 0.5

**Status:** código de integração preparado e testado de forma isolada. A versão cartográfica pública permanece **0.4.0** até implantação, comprovação da coleta e autorização expressa para publicar posições. **Não há GPS real publicado automaticamente.** Não simular veículos ou ETA.

## Fonte de dados e relacionamento

O APK GoBus 1.29.1.2 implementa GET/JSONP sob a praça `MPA`. A TACOM identificou Canoas com `codcid=4`. O frontend **não acessa** o HTTP legado, que permanece restrito ao worker privado.

O coletor `transporte.gobus_live` consulta somente:

1. `V3/buscarPrevisoes/{codParada}/false/0/MPA/retornoJSON` para IDs de paradas efetivamente inventariados e localizados em Canoas;
2. `V3/retornaVeiculosMapa/{codItinerario}/0/MPA/retornoJSONVeiculos` para itinerários que foram **observados naquela rodada** com identificadores de veículos em previsões;
3. Os IDs de itinerário são cruzados com os **57 itinerários de referência** existentes em `public/data/route-shapes.geojson`, segundo `source_route_code` e `association_method=city4_exact_code_and_prediction_itinerary`. Não se usa associação por nome, sequência presumida ou enumeração de IDs.

Somente pares de veículo/itinerário que aparecem na previsão e no retorno de veículos entram no feed. A coordenada é validada dentro do envelope operacional e da união dos bairros com buffer de 250 metros. A configuração default escolhe oito paradas distribuídas ao longo do inventário a cada rodada; não consulta as 1.410 paradas em ciclos de 15 segundos. A amostra **não prova que todos os ônibus tenham sido localizados**.

## Base temporal: essencial para interpretação correta

`observed_at` e `fetched_at` são iguais **exclusivamente para compatibilidade com o contrato do worker**, com `time_basis=client_fetch` e `source_observed_at=null`. Eles indicam **hora da consulta HTTP**, não medição GPS embarcada. O cliente da TACOM não documenta timestamp de origem no objeto de veículo analisado.

- `signal_status=ok`: a consulta retornou coordenada, não um certificado de atualização GPS;
- `signal_status=SC`: sem comunicação, posição potencialmente retida;
- `signal_status=SG`: sem GPS, posição potencialmente retida;
- `bearing`: `direcao` 0–7 multiplicado por 45 graus, marcado `bearing_basis=apk_octant_north_unverified`. **A hipótese de que 0 corresponde ao Norte ainda exige verificação da TACOM**. SC/SG implicam `bearing=null`;
- `stale_polls`: quantidade de consultas consecutivas sem mudança de coordenada. **Não comprova veículo parado, cancelamento nem falha da operadora**;
- `route_relation=reference_not_homologated`: associação TACOM→NGS baseada em código/itinerário observado, não equivalência contratual homologada.

O banco guarda metadados na coluna JSON `position.payload`, sem exigir migração estrutural da tabela; o histórico permite auditoria metodológica. A API pública retém apenas posições de até **180 segundos** pelo horário de consulta e não extrapola posições. O algoritmo `audit-0.2.0` classifica eventos temporais com essa base como **inconclusivos**; não calcula velocidade praticada com intervalos entre consultas.

## Operação privada: teste único sem persistência de GPS

Instalar as dependências do projeto e executar em máquina da equipe autorizada:

```bash
PYTHONPATH=pipeline python -m transporte.gobus_live \
  --authorized --accept-plain-http \
  --interval 15 --max-requests 16 \
  --stop-queries 8 --itinerary-queries 6
```

O resultado normalizado é gravado em `var/gobus/live-feed.json`, e o estado de consultas em `var/gobus/live-state.json`. Ambos são **privados e ignorados pelo Git**; não utilizar `public/data/vehicles.json`. Capturas JSONP, IDs individuais e coordenadas não são exibidos nos logs do coletor.

Para uma **sondagem efêmera sem salvar coordenadas e sem publicá-las**, há `scripts/gobus_probe_live_once.py`: até dez GET, amostra de seis paradas e até três itinerários identificados, com pelo menos 15 s entre consultas; imprime apenas contagens e estados agregados. Não executar repetidamente como scheduler.

```bash
PYTHONPATH=pipeline python scripts/gobus_probe_live_once.py \
  --authorized --accept-plain-http
```

Não existe fallback para endpoints PNE, alarme, avisos, registro de uso ou escrita. Redirecionamentos e HTTP 401/403 suspendem a coleta; 429 e falhas transitórias obedecem espera limitada e orçamento. Sem autorização expressa, não executar o coletor.

## Operação persistente e API HTTPS

O arquivo `compose.yaml` mantém o worker original de feed normalizado e acrescenta **`gobus-live`**, em perfil opt-in; não é iniciado por padrão. O worker TACOM lê o cadastro de referência do build da imagem, insere somente registros válidos no PostgreSQL e grava estado em volume privado persistente `gobus_private`.

Configurar no servidor municipal (nunca no frontend):

```ini
POSTGRES_PASSWORD=<senha-aleatoria-no-servidor>
ADMIN_API_KEY=<segredo-privado-com-pelo-menos-32-caracteres>
GOBUS_READ_AUTHORIZED=true
GOBUS_ACCEPT_HTTP=true
GOBUS_REQUEST_SPACING=15
GOBUS_CYCLE_SECONDS=180
SOURCE_HOMOLOGATED=false
PUBLIC_POSITIONS_ENABLED=false
```

Amostra do procedimento após validação técnica de rede, segurança e autorização:

```bash
docker compose up -d db api
docker compose --profile gobus-live up -d gobus-live
docker compose logs --tail 40 gobus-live
```

A coleta persistente **não liga automaticamente a publicação pública**. Depois de verificar dados, qualidade e permissão de redistribuição, configurar `PUBLIC_POSITIONS_ENABLED=true` **somente na API**, mantendo `SOURCE_HOMOLOGATED=false` enquanto não houver timestamps GPS de origem e contrato plenamente validado. Nesse modo `GET /v1/vehicles` retorna `status=reference`, metadados de consulta e no máximo três minutos de posições; `status=available` continua reservado à fonte temporalmente homologada. A API inclui rate limit por IP de conexão (60 req/min, em memória); o Nginx do ambiente deve aplicar a limitação adicional para múltiplas réplicas.

No `GitHub Pages`, publicar **apenas a URL HTTPS da API própria** pela variável `VITE_PUBLIC_API_BASE`, durante o build. Não inserir URL HTTP da TACOM, credenciais ou JSONP bruto. O navegador busca `/v1/vehicles` a cada 60 s quando visível e reduz consultas quando a aba está oculta; ambos MapLibre e Leaflet representam idade da consulta e estados de sinal.

**Um proxy HTTPS da API municipal NÃO autentica o trecho HTTP municipal → TACOM.** Negociar origem HTTPS/TLS, VPN ou canal privado autenticado com o fornecedor. O Nginx só protege o trecho público browser → API; é insuficiente para garantir a integridade do fornecedor legado.

## Implantação HTTPS completa no Docker Compose

O perfil opcional `edge` executa `nginx:stable-alpine` na porta interna 8443, publicada como 443 no host. Há dois limites de requisição: Nginx por IP real do cliente (30 GET/min em `/v1/vehicles`) e API por endereço remoto confiável (padrão 60/min). A porta de aplicação 8000 fica vinculada somente a `127.0.0.1` no host, e o navegador nunca acessa o HTTP da TACOM.

**Pré-requisitos fora do GitHub:** servidor/VPS ou host municipal com Docker, DNS próprio, certificado TLS válido e chave correspondente, armazenamento persistente, configuração de backups e concordância formal com o regime de dados GPS. Não há servidor de produção nem DNS configurados automaticamente no repositório.

Após providenciar os certificados, mantenha **`fullchain.pem` e `privkey.pem` fora do Git** no diretório `TLS_CERT_DIR`, protegido por permissões do sistema. A pasta local `infra/certs` está em `.gitignore`. Em `.env` do servidor, defina `API_HOST=nome-real-do-domínio`, `TLS_CERT_DIR`, `PUBLIC_ORIGINS=https://marcianolima.github.io` e as credenciais privadas em variáveis locais. Só então:

```bash
docker compose --profile gobus-live --profile edge config --quiet
docker compose --profile edge up -d db api edge
curl --fail --silent --show-error https://SEU-DOMINIO-API/v1/health
# Em seguida, após validação da rede/contrato TACOM:
docker compose --profile gobus-live up -d gobus-live
# Aceite com dois GETs sanitizados, sem exibir coordenadas:
PYTHONPATH=pipeline python scripts/check_gobus_deployment.py --api https://SEU-DOMINIO-API
```

**Importante:** `SEU-DOMINIO-API` é apenas placeholder e deve ser substituído pelo FQDN real, com TLS válido. Não usar certificados autofirmados em produção. O `nginx` será fail-closed sem os certificados; não disponibilizar fallback HTTP para o browser.

No cenário em que muitos usuários compartilham uma única conexão do proxy no backend, **não** confiar indiscriminadamente em cabeçalhos `X-Forwarded-For`. O Nginx sobrescreve `X-Real-IP` com o endereço real do cliente. O FastAPI só interpreta esse cabeçalho quando o IP do container de proxy pertence explicitamente a `TRUSTED_PROXY_CIDRS` configurado pelo operador. Para confirmar o endereço do container consulte `docker inspect` e configure apenas o IP/CIDR controlado, nunca redes arbitrariamente amplas. Alternativamente, aumente `PUBLIC_API_LIMIT_PER_MINUTE` com cautela, mantendo a limitação por IP na borda Nginx.

Para o GitHub Pages consultar a API: configurar a variável de repositório (não segredo) `VITE_PUBLIC_API_BASE=https://SEU-DOMINIO-API` em **Settings → Secrets and variables → Actions → Variables**, executar novamente o workflow de build e verificar as permissões CORS. Credenciais TACOM/administrativas não devem ser cadastradas em variáveis `VITE_`.

O código do coletor mantém tetos **persistentes** conservadores, inicialmente `GOBUS_MAX_PER_HOUR=120` e `GOBUS_MAX_PER_DAY=1000`. Os limites são valores operacionais iniciais, **não representam cotas concedidas pela TACOM**. Negociar com a TACOM a frequência e o número de chamadas adequados. Em caso de limite 429 ou orçamento esgotado, o worker suspende novas consultas.

## Operação, segurança e limites

- Limitar a **uma instância** do worker TACOM; manter disco e Postgres com backups e acesso restrito.
- Registrar escopo, finalidade, bases legais, condições de redistribuição e prazo de retenção de telemetria antes de ativação pública; dados históricos brutos permanecem restritos à gestão.
- Monitorar `source_id`, número de consultas, taxa de erros, respostas vazias, diferença entre consultas e `SC/SG`; não registrar payloads com identificadores de veículo em CI.
- Não atribuir velocidade, parada prolongada, infração ou viagem não realizada a dados sem timestamp GPS de origem.
- Iniciar com coleta monitorada, aferir respostas e limites, e desativar se houver 401/403/429 prolongado ou inconsistência de município.
- Reconstruir a imagem `gobus-live` após atualizar `route-shapes.geojson`, `stop-inventory.json` ou bairros; a imagem inclui snapshot destas três referências.
- Frontend estático e os PMTiles permanecem independentes do worker. Falha do GPS não apaga percursos/paradas.

## Testes e validação

Os testes usam `httpx.MockTransport`, sem rede, e cobrem octantes e vírgula decimal, SC/SG, payload singular/plural, source temporal, deduplicação, estado entre rodadas, autorização de publicação, controle de tráfego, 403 e escopo municipal. O CI geral `ci-pages.yml` executa toda a suíte; o workflow específico `gobus-live-tests.yml` é também **offline**.

**Não considerar versão 1.0 homologada** até a TACOM disponibilizar tabela linha↔sublinha↔itinerário↔sentido↔vigência, origem segura e timestamps GPS/SLA. Ver [ofício técnico](OFICIO-TACOM-GPS.md).
