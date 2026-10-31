# Status de implantação e aceite operacional — WebGIS Transporte Canoas

Data de referência: 31/10/2026. Esta lista distingue **código concluído** de **serviço efetivamente instalado**.

## Estado atual

| Item | Resultado |
| --- | --- |
| WebGIS cartográfico no GitHub Pages | Publicado com dados de referência; não possui telemetria ativa |
| Dados TACOM de referência | 57 itinerários e 1.410 paradas; sem equivalência contratual de viagens |
| Descoberta de pares veículo + itinerário | Adaptador escrito; testes offline com `httpx.MockTransport` |
| Leitura de posições TACOM | Código HTTP GET/JSONP escrito; produção não comprovada nesta entrega |
| Normalização temporal | `client_fetch`, `source_observed_at=null`, SC/SG e octantes implementados |
| Auditoria, armazenamento e consulta | Código, testes de integração e API implementados; sem banco persistente instalado aqui |
| Controle de tráfego TACOM | Mínimo 15 segundos entre GET; limite por ciclo, por hora e por dia; 429 suspende |
| Publicação de posição na API | **Bloqueada por padrão** e exige `PUBLIC_POSITIONS_ENABLED=true` independentemente de `SOURCE_HOMOLOGATED` |
| Exposição no frontend | Preparada com MapLibre/Leaflet e metadados; sem endpoint HTTPS de produção configurado nesta sessão |
| Segurança de borda | Compose com Nginx HTTPS opcional e certificados fora do Git |
| Certificado/domínio/servidor da API | **Não provisionados neste projeto** |
| Prova de ônibus em tempo real | **Não confirmada ainda; nenhum ônibus foi inventado** |

## Checklist para o responsável por infraestrutura

- [ ] Designar host municipal (ou homologar explicitamente provedor externo), controle de acesso e retenção histórica.
- [ ] Providenciar domínio DNS da API e certificado TLS válido. A origem TACOM continua HTTP e exige avaliação de canal seguro privado com fornecedor.
- [ ] Provisionar banco PostgreSQL/PostGIS persistente e backups com política administrativa definida.
- [ ] Configurar `.env` privado e limites acordados com TACOM; não adicionar ao repositório.
- [ ] Rodar `docker compose --profile edge --profile gobus-live config --quiet`; depois instalar `db`, `api` e `edge` com TLS.
- [ ] Consultar `GET /v1/health` com HTTPS; enquanto não houver coleta o resultado `not_configured` é válido.
- [ ] Provar consulta autorizada e restrita via `PYTHONPATH=pipeline python scripts/gobus_probe_live_once.py --authorized --accept-plain-http` na rede da TACOM; a amostra publica somente contagens.
- [ ] Iniciar o worker privado e verificar `/v1/health` e o histórico restrito antes de divulgar. A ausência de previsão/posição não comprova cancelamento.
- [ ] Conferir a autorização de redistribuição; habilitar separadamente `PUBLIC_POSITIONS_ENABLED=true` **somente se autorizado**, mantendo `SOURCE_HOMOLOGATED=false` sem timestamp GPS de origem homologado.
- [ ] Executar `PYTHONPATH=pipeline python scripts/check_gobus_deployment.py --api https://DOMINIO-VALIDADO` e exigir zero erros no resumo sanitizado.
- [ ] Configurar `VITE_PUBLIC_API_BASE=https://DOMINIO-VALIDADO` nas variáveis do repositório GitHub; repetir Actions e testar MapLibre/Leaflet no celular e no desktop.
- [ ] Homologar acesso jurídico/contratual e critérios de auditoria, com revisão técnica de `SC`, `SG`, direção, itinerários e carimbo de tempo GPS.

## Condições de bloqueio

Não promover à produção se ocorrer qualquer um dos seguintes problemas: publicação de coordenadas em `public/data`, segredo no frontend, HTTP de origem exposto ao navegador, API pública sem autorização explícita, dados com município indefinido, resposta temporal declarada `source_gps` sem timestamp original verificado, redirecionamento inesperado, repetidas falhas 429/403, ou perda de persistência/controle de quotas.

**Dados de referência não são provas de viagem realizada, falha da operadora ou infração.** A disponibilidade do código e a aprovação do CI não equivalem à homologação do serviço.
