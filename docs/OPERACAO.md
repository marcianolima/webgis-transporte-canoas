# Desenvolvimento, produção e recuperação

## Ambiente de desenvolvimento

Requisitos: Node 22+, npm, Python 3.12+. Na raiz do repositório:

```bash
npm ci
python -m venv .venv
.venv/bin/pip install -r requirements.lock
npm run dev
```

A base Vite é `/webgis-transporte-canoas/`. Para outra base, definir `VITE_BASE_PATH`. URL pública esperada: `https://marcianolima.github.io/webgis-transporte-canoas/`. Rotas usam fragmentos e não dependem de rewrite no Pages.

```bash
npm run lint
npm test
npm run build
PYTHONPATH=pipeline .venv/bin/pytest -q
PYTHONPATH=pipeline .venv/bin/python scripts/validate_public.py
```

## Coleta estática NGS

```bash
PYTHONPATH=pipeline .venv/bin/python -m transporte.collect --days 5
python scripts/prepare_catalogue.py
PYTHONPATH=pipeline .venv/bin/python scripts/validate_public.py
npm run build
```

Até duas conexões, intervalo global de 0,75 s, cache por URL, até duas novas tentativas. `--interval` aceita ajuste para diminuir a carga (mínimo 0,5 s). Não coleta GPS. Datas e número de linhas variam conforme a publicação da operadora. A execução pode levar vários minutos. Falha total não substitui o último arquivo válido; falha parcial acompanha erros por linha/data. Verificar `status` e não apenas código de saída: publicação parcial é permitida, nunca declarada completa.

O cache tem TTL de 1 h para datas, 24 h para cadastro/horários e 7 dias para itinerário textual. Para revalidar alteração urgente, remover **somente** a entrada correspondente do cache ou reduzir o TTL no adaptador após avaliar o limite da fonte. Conservar `var/static-history.sqlite` em disco persistente se a coleta ocorrer na infraestrutura municipal.

`refresh_cartography.py` faz atualização manual das duas bases de referência e recalcula produtos territoriais. Rever diff, hashes e metadados antes de publicar; não confundir hora de processamento com nova validação do serviço municipal original.

## GitHub Actions e Pages

`.github/workflows/ci-pages.yml` executa testes, lint, build e deploy em push na `main`. Pull requests só validam. Coleta estática diária às **05h20 em Brasília (08h20 UTC)**, sem garantia de execução exata. `workflow_dispatch` pode atualizar os dados com `refresh_data=true`.

A execução agendada usa cache e arquiva evidências e o histórico estático por 30 dias em artefatos do Actions. Cache do Actions pode ser removido por políticas da plataforma; não é armazenamento histórico municipal definitivo. O deploy agendado publica o snapshot gerado pelo próprio job, sem criar commit automático dos arquivos atualizados. O artefato e o run identificam o conteúdo publicado; o commit identifica o código.

Para primeira publicação, **Settings → Pages → Source: GitHub Actions**. A conexão GitHub deve poder gravar workflows; a conta mantém a configuração administrativa de Pages. Verificar o run `Testes, dados estáticos e GitHub Pages`, job deploy e URL. Workflow escrito ou build local não são prova de publicação.

## API e worker persistentes

A API tem SQLite para testes locais e PostgreSQL em produção. O modelo complementar ativa PostGIS. O worker recebe um feed normalizado **após homologação**; não funciona diretamente com um contrato TACOM desconhecido.

1. Copiar `.env.example` para `.env` no servidor e preencher `POSTGRES_PASSWORD` e `ADMIN_API_KEY` com valores privados (mínimo de 32 caracteres para a chave). Caracteres da senha em `DATABASE_URL` precisam de codificação adequada; preferir segredo aleatório alfanumérico.
2. Implantar API e banco: `docker compose up -d --build db api`.
3. Configurar virtualhost TLS municipal com base em `infra/nginx.conf.example`. Porta 8000 fica ligada somente ao loopback; banco sem porta pública.
4. Configurar `PUBLIC_ORIGINS` com a origem do Pages. Publicar somente `/v1` para cidadãos se a política municipal assim exigir; manter `/admin` e `/internal` em rede restrita ou VPN.
5. Para integrar o frontend público, definir `VITE_PUBLIC_API_BASE` na configuração de build, contendo **apenas a URL pública**, e reconstruir. Nenhum segredo VITE.
6. Validar feed, autorização, frequência, source IDs e código municipal. Definir `SOURCE_HOMOLOGATED=true`, `GPS_FEED_URL` HTTPS sem query/credenciais, `GPS_FEED_ALLOWED_HOST`, token opcional e intervalo autorizado (mínimo técnico 30 s).
7. Só então iniciar: `docker compose --profile gps up -d worker`.

O worker rejeita redirects, redes não municipais, timestamps sem fuso e coordenadas fora da área operacional. Registra contagens e classe de erro sem vazar tokens. Falhas aumentam o intervalo até 15 min. O processo permanece desligado quando a fonte não está homologada. Alertas: falha do job no Actions e logs estruturados do worker; integrar esses sinais ao monitoramento municipal. Envio por e-mail/Slack não está configurado.

Teste local da API (com chave definida no próprio ambiente, sem colocá-la na linha de comando):

```bash
PYTHONPATH=pipeline:. .venv/bin/uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8000
```

Painel privado: `/admin`; usuário Basic `admin`, senha `ADMIN_API_KEY`, apenas sob TLS em produção. Identidade técnica compartilhada: substituir por autenticação municipal com usuários nominais antes do uso multiusuário. Não há OIDC, gestão de perfis nem recuperação de senha implementados.

## Backup, retenção e restauração

`BACKUP_DIR=/diretorio/protegido sh infra/backup.sh` gera dump PostgreSQL e checksum fora do Git. Não comitar backups. Verificar periodicamente em banco separado:

```bash
docker compose exec -T db pg_restore -U transporte --clean --if-exists --dbname BANCO_DE_TESTE < arquivo.dump
```

A política de retenção deve acompanhar a finalidade municipal. O projeto não apaga evidências automaticamente. Definir janelas e rotinas no ambiente operacional, protegendo ocorrências/revisões necessárias à auditoria. Projetar particionamento e rotação conforme volume real. Conservar também configuração privada, versões de imagens e histórico estático.

Recuperação: manter último frontend válido; restaurar banco de backup testado; revalidar secrets no servidor; subir API; conferir `/v1/health`; executar um ciclo controlado do worker; conferir atualidade sem declarar ausência de GPS como ausência de operação. Para reverter frontend, redeploy do commit estável pelo Actions.

## Limite de homologação da infraestrutura

API/SQLite e contratos foram testados localmente. Docker/PostgreSQL/PostGIS, TLS e worker alimentado por uma fonte municipal real ainda precisam ser executados na infraestrutura de destino. Os arquivos de infraestrutura não representam serviços já provisionados.

## Compatibilidade cartográfica

MapLibre é o renderizador principal. Se WebGL não estiver disponível, a aplicação usa Leaflet/SVG com os mesmos polígonos locais. O fundo viário OSM é opcional e vem desligado: assim o mapa territorial abre sem depender de tiles ou chaves externas. O navegador de teste recebeu tiles de bloqueio do servidor OSM; esse fato não invalida as camadas locais. Para publicação, respeitar a política do fornecedor de tiles; não prefetch, não proxy para contornar bloqueios. Nenhuma chave CARTO ou de terceiros foi incorporada.
