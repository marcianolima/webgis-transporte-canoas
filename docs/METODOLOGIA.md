# Indicadores, qualidade e limites de inferência

## Princípios

Distinguir programação, observação, processamento e inferência. Nulo significa indisponível; zero só é usado para uma contagem efetivamente observada em um conjunto validado. Fixture sintética só existe em testes. Uma interface construída não equivale a integração homologada.

## Indicadores publicados

| Produto | Cálculo | Amostra / período | Limite |
| --- | --- | --- | --- |
| Linhas publicadas | IDs distintos no cadastro da data | Uma data exata da NGS | Não é frota nem confirmação de operação |
| Saídas programadas | Contagem de registros por data, linha, sentido | Registros validados; falhas por linha são listadas | Não comprova realização |
| Oferta por hora | Saídas agrupadas pela hora módulo 24 | Inclui madrugada seguinte identificada por +1 | Não equivale a passagens por parada |
| Intervalo programado | Diferença entre saídas consecutivas, separadamente por sentido | `n` intervalos; média ponderada dos intervalos dos sentidos | Mistura períodos do dia; não mede regularidade observada |
| Área do bairro | Área em EPSG:31982 / 1.000.000 | Polígono de bairro | Não usar graus para distâncias |
| População do bairro | Atributo `POPULACAO_2022` da base de referência | Censo 2022, conforme arquivo reutilizado | Não é estimativa atual ou população atendida |
| Densidade populacional | População / área de referência | Bairros ou setores | Coroplético de contexto territorial, não de oferta de ônibus |

Horários são preservados na ordem de origem. Transição 23h → 00h no final da sequência é convertida em minutos de serviço acima de 1440. Sequências fora de ordem em outros horários são rejeitadas, sem ordenar silenciosamente. Partidas distintas no mesmo minuto e sentido preservam sua sequência.

## Motor operacional preparado

Versão: `audit-0.1.0`. Não há execução homologada sobre GPS real de Canoas. A bateria de testes usa dados sintéticos isolados.

| Regra | Requisitos e limiar | Resultado |
| --- | --- | --- |
| Salto GPS | Mesmo veículo/fonte/linha, Δt até 180 s; distância geodésica GRS80 / tempo > 100 km/h | Inconclusivo; possível erro de localização, não velocidade instantânea |
| Lacuna de amostragem | Δt > 180 s | Inconclusivo; não gera cancelamento |
| Conflito no mesmo instante | Coordenadas distintas para veículo/fonte/instante iguais | Inconclusivo; preserva ambas no histórico |
| Afastamento de trajeto | Duas posições com Δt até 90 s, ambas > 100 m da geometria homologada | Provável afastamento; conferir versão, precisão e desvio autorizado |
| Movimento interrompido | ≥ 4 amostras, ≥ 10 min, lacunas até 180 s, raio 30 m da primeira | Inconclusivo; terminal e congestionamento são explicações possíveis |
| Intervalos observados | ≥ 3 passagens confirmadas no mesmo ponto, linha e sentido | Média, mediana e CV populacional; `n` intervalos |

O worker executa consistência temporal, saltos, conflitos e movimentos interrompidos. Não há extração automática homologada de passagens, map matching, associação a viagens, ETA, detecção de comboios, velocidade comercial, tempo de percurso, trechos lentos ou comparação contratual. A função de intervalos recebe passagens já identificadas; não recebe GPS bruto. A regra de afastamento não executa no worker sem um shape válido e sua dimensão temporal.

Toda ocorrência preserva evidências e versão do algoritmo e marca `is_infraction=false`. “Confirmada” só pode ser registrada em revisão humana autenticada e fundamentada; não é emitida pelo motor. Um parecer administrativo deve conferir o suporte documental necessário ao caso.

## Análise territorial

Bairros: [GeoCanoas / BAIRROSOFICIAL](https://geo.canoas.rs.gov.br/server/rest/services/BAIRROSOFICIAL/FeatureServer), reutilizados do arquivo do [WebGIS Empreender](https://github.com/marcianolima/webgis-empreender-canoas/blob/main/public/data/bairros-oficiais.geojson). Setores: 659 feições com código municipal 4304606 e população de referência 2022 do mesmo projeto. Validação local: contagens, identificadores, geometrias, coordenadas e transformação de referência. O servidor municipal original não foi revalidado devido à resposta 503 neste ambiente.

O contorno tracejado é a união topológica dos bairros. Não o denominamos limite municipal oficial homologado. O arquivo simplificado `canoas.geojson` do outro projeto não foi usado como limite oficial. Malha IBGE direta: tentativa sem sucesso neste ambiente.

O cálculo de buffer de 300 m está implementado, mas retorna nulo sem paradas. Não distribui população proporcionalmente à área. Proximidade euclidiana não considera barreiras, acessos, travessias, linhas atendidas, calendário ou frequência. Atendimento a escolas/unidades de saúde, extensão de linhas por bairro e acessibilidade por rede permanecem pendentes de cadastro geográfico de transporte e reconciliação das bases.

## Atualidade e qualidade

- Frontend descarta posições observadas há mais de 180 s e acima de 30 s no futuro. Reavalia idade a cada 15 s, independentemente da atualização do feed.
- API pública também aplica janela de 180 s. Não interpola posições nem apresenta veículos estimados.
- Timestamps sem fuso, coordenadas inválidas, IDs ausentes, valores não finitos e registros fora do escopo municipal são rejeitados.
- Serviço estático exibe alerta quando a coleta passa de 48 h. Não existe garantia de atualização pontual por GitHub Actions.
- Cada data informa linhas esperadas, falhas e completude do recurso de horários. Completude da coleta não comprova completude da rede operacional.
- Schemas inesperados impedem considerar o recurso bem sucedido. Falha total preserva o último arquivo publicado. Falha parcial é explicitada.
