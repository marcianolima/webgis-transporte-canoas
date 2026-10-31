# Minuta de ofício — Integração técnica TACOM/Sogal e WebGIS Transporte Canoas

**OFÍCIO Nº [a preencher]/2026 — [unidade responsável]**

Canoas/RS, [data de expedição].

**À TACOM — Equipe Técnica de Sistemas de Transporte**  
**Com ciência à concessionária/operadora responsável e à Sogal/NGS, conforme competências contratuais.**

**Assunto:** Solicitação de documentação técnica, canal seguro de integração e parâmetros de uso dos dados de localização e itinerários do transporte coletivo de Canoas/RS.

Prezados(as),

A Prefeitura Municipal de Canoas, por intermédio da área responsável pela gestão da informação geoespacial e em articulação com os órgãos municipais competentes de transporte e fiscalização, desenvolve uma plataforma WebGIS destinada à consulta pública do sistema de transporte coletivo e ao apoio técnico à gestão e à auditoria operacional.

No âmbito de uma avaliação técnica autorizada do aplicativo Canoas GoBus e da programação disponibilizada pela Sogal/NGS, foram identificadas funcionalidades de consulta de itinerários geográficos, paradas, previsões e localização de veículos. A identificação do município de Canoas foi observada no serviço SIU Mobile associado à praça `MPA`, com código municipal `codcid=4`. Para assegurar a confiabilidade, a segurança e a interpretação correta dos dados, solicitamos as seguintes informações e providências:

1. **Identificadores e relacionamento das linhas:** tabela atualizada de `codLinha`, código público da linha, `codSublinha`, `codItinerario`, sentido, variante, tipo de serviço, vigência inicial/final e órgão responsável, com correspondência, quando existente, aos identificadores e quadros de horários da Sogal/NGS. Esclarecer como são tratados serviços históricos, metropolitanos e municipais.
2. **Localização dos veículos:** documentação dos campos de `retornaVeiculosMapa`, `retornaVeiculoEmbarcado` e mecanismos oficiais equivalentes, incluindo formato e referencial das coordenadas, identificador estável do veículo, atualização da fonte, qualidade da medição, estados `SC` e `SG`, significado de `direcao` (octantes 0–7, inclusive orientação de 0°) e disponibilidade de **timestamp original da medição GPS** distinto do horário de resposta HTTP.
3. **Pontos de parada e previsões:** cadastro municipal vigente, códigos, localização, sentidos, sequência por itinerário, data de atualização, método de cálculo de previsão de chegada, significado dos campos `sgLin`, `prev`, `numVeicGestor` e `codItinerario`, bem como critérios para diferenciar indisponibilidade de dados de ausência de veículos.
4. **Canal de integração seguro:** API de leitura por HTTPS/TLS, ou acesso privado autenticado equivalente, documentação formal, ambiente de homologação, gestão de credenciais, política de IPs autorizados e notificações de mudança de esquema. Não se prevê incluir credenciais ou serviços HTTP legados no frontend público.
5. **Condições de operação e tratamento de dados:** limites de chamadas por minuto e por dia, frequência máxima permitida de consulta, períodos de retenção, requisitos de disponibilidade e suporte, SLA e tratamento de respostas 429/503. Solicita-se esclarecer a possibilidade de armazenamento de histórico institucional e de divulgação pública de **posições recentes**, com a indicação de origem e limitação temporal, sem identificação de motoristas ou passageiros.
6. **Validação cartográfica:** disponibilização de rotas, variantes e paradas em GeoJSON ou GTFS/GTFS-Realtime, caso disponíveis, com referência espacial, vigência, metadados e informações sobre trechos de circulação intermunicipal.

A finalidade é utilizar exclusivamente dados obtidos por mecanismos autorizados, distinguindo programação, observação, processamento e inferência. A falta de uma posição GPS não será considerada comprovação automática de cancelamento, falha contratual ou infração. Eventos eventualmente relacionados à fiscalização dependerão de fontes verificáveis, critérios validados e revisão humana.

Solicitamos, se possível, a indicação de um ponto focal técnico para reunião de alinhamento, fornecimento do dicionário de dados e definição de um procedimento de homologação compartilhado.

Permanecemos à disposição para apresentar a arquitetura prevista, as regras de proteção de dados e um ambiente de validação controlado.

Atenciosamente,

**[Nome e cargo da autoridade signatária]**  
[Secretaria ou órgão responsável]  
Prefeitura Municipal de Canoas — RS  
[Contato institucional]

---

**Uso interno:** minuta sujeita à revisão da secretaria de transporte competente, da assessoria jurídica e da gestão contratual antes do envio. Não constitui declaração de homologação da TACOM, autorização de redistribuição nem compromisso formal de SLA.
