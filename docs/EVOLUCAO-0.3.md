# Versão 0.3.0 — geometrias reais de linhas e paradas

Investigação e coleta: **31/10/2026**, America/Sao_Paulo. Base de código inicial desta revisão: `21e7e34a36d11f6156b501133371fec51dcdc6b3`. Os avanços anteriores de análise do APK, parsing, sondagens, correspondências e staging foram preservados.

## Resultado

- **52 itinerários geográficos de 35 linhas**, como referência da API TACOM/SIU Mobile.
- **215 paradas georreferenciadas**, associadas por ID às listas de linhas municipais consultadas.
- **38 listas de paradas**, selecionadas entre os códigos coincidentes e a programação NGS de 31/10/2026; **1.266 IDs distintos** nessas listas. Não foram obtidas coordenadas de todos esses IDs.
- Dez consultas amostrais de previsões forneceram relações reais entre código de linha e `codItinerario`. A finalidade foi descobrir geometria, sem publicar previsões efêmeras ou IDs de veículos.
- A base NGS permanece com 81 IDs e 4.990 saídas no snapshot de 30/10/2026. Coincidência de código não homologa equivalência de nome, sentido, variante, programação ou vigência.
- PMTiles v3/MVT: **479.399 bytes, 28 tiles**, camadas de 18 bairros, 659 setores, 52 itinerários, 215 paradas e contorno derivado.

Estatísticas, origem, hashes, datas, recursos consultados e limitações estão em `public/data/transport-geography.json`. Cada feição conserva URL, SHA-256 da resposta e horário de obtenção. JSONP bruto e respostas com identificação de veículos ficam em `var/gobus/`, fora da publicação e do cache público de Actions.

## Correção decisiva na engenharia reversa

No acesso testado, `V3/buscarParadasPorLinhaComCoordenadas` devolveu **a mesma resposta de 64 paradas de Viamão** para as linhas 5000, 05000 e 05006, inclusive com callback/cache-buster compatíveis com o cliente. O teste anterior por envelope amplo aceitava esses pontos porque a caixa de coordenadas também incluía Viamão. **Essa amostra anterior não confirma paradas de Canoas.** Nenhum desses pontos foi aproveitado.

A consulta `V3/buscarParadasPorLinha/5000/0/MPA/retornoJSON` retornou 71 registros coerentes com Mathias Velho, incluindo o ID 8746. O recurso observado no APK `buscarDadosParada/8746/0/retornoJSONPontosItinerario` forneceu coordenadas na Rua Florianópolis, em Canoas. Consultar previsões dessa parada retornou IDs de itinerários das linhas 05000, 05001 e 05030. Esses IDs foram usados diretamente em `V3/buscarItinerario`; **não houve enumeração de IDs nem reconstrução por segmentos entre paradas**.

O itinerário 2457 retornou 69 vértices e 8,9507 km. Outros itinerários obtidos da mesma fonte têm coordenadas diferentes e percursos coerentes com a rede. A origem continua sendo o HTTP legado configurado no APK; o Pages lê apenas os produtos estáticos locais e não faz consultas HTTP ao fornecedor.

## Método e qualidade territorial

1. Confirmar `CANOAS=codcid 4` pelo serviço `V3/cidadesLinhas/MPA`; filtrar `buscarLinhas` por município e praça MPA.
2. Associar códigos exatos unívocos ao catálogo NGS, mantendo os nomes de ambas as fontes como dimensões diferentes. São 72 candidatos; isso não os torna equivalentes operacionalmente.
3. Consultar listas de paradas por linha e cruzar seus IDs com coordenadas de consultas por proximidade e pelo recurso individual.
4. Publicar apenas paradas associadas a essas listas e situadas na união dos bairros ou em seu buffer de 250 m, calculado em EPSG:31982. Identificar bairro por interseção, sem atribuição por vizinho mais próximo.
5. Observar relações `sgLin/codItinerario` em previsões de paradas municipais já verificadas. Recuperar os vértices do itinerário preservando a ordem da API.
6. Exigir comprimento de 0,2–100 km, ao menos 80% do comprimento no buffer de 250 m e distância máxima dos vértices de 1.500 m da união dos bairros. Dados incompatíveis são separados para revisão.

**Sete itinerários têm sinalização `territorial_quality=border_review`**: entre 87% e 94% de seu comprimento está no buffer, e os trechos mais distantes ficam até aproximadamente 1,1 km da união dos bairros. A geometria foi preservada sem recorte e marcada para revisão. Isso não declara circulação fora de limite autorizado: a união dos bairros **não é limite municipal homologado**. Não adotar esses limiares como regra de infração.

Todas as feições são `status=reference`, `homologated=false`. O sentido, a validade e a totalidade das variantes não são informados por esse contrato. O vínculo com NGS é declarado como candidato por código exato; os itinerários vieram de relações observadas na API. A coleta cobre somente a amostra disponível, não todos os serviços ou períodos.

## Interface

- Seleção de uma ou várias linhas, cores estáveis, desenho e enquadramento dos percursos reais.
- Paradas filtradas pelas linhas selecionadas, com opção de exibir/ocultar e popup de origem, data e vínculos.
- Ficha da linha com mapa e download GeoJSON do percurso.
- Página de paradas com busca, filtros de linha/bairro, paginação, foco no mapa e exportação CSV/GeoJSON.
- Identificação TACOM correta: removidos os rótulos e links OSM que não correspondiam à nova fonte.
- Estatísticas territoriais calculadas sobre a **amostra**, sem extrapolar atendimento total, população coberta ou operação efetiva. Extensão é a união geométrica exata dos traçados. Segmentos coincidentes são unidos; traçados próximos ou paralelos com coordenadas diferentes continuam distintos. Não é extensão viária nem rede autorizada.

## Operação e atualização

```bash
PYTHONPATH=pipeline .venv/bin/python -m transporte.gobus_geography \
  --authorized --allow-plain-http --service-date today \
  --max-requests 180 --interval 2
PYTHONPATH=pipeline .venv/bin/python -m transporte.publish_geography
.venv/bin/python scripts/prepare_catalogue.py
PYTHONPATH=pipeline .venv/bin/python scripts/validate_public.py
npm run build
```

O primeiro comando exige autorização compatível com a fonte e uso explícito do transporte HTTP legado. Usa duas conexões no máximo, intervalo global mínimo de 1,5 s, orçamento máximo de 300 GET por execução, cache estático de 24 h e cache de previsões de cinco minutos. 401/403 interrompem novas requisições. Redirects são rejeitados. Não executa scripts JSONP, não consulta cartões, não emite avisos e não registra uso no fornecedor. Não é coletor contínuo de GPS.

O workflow de Pages possui opção manual `refresh_geography=false` por padrão. A rotina diária existente continua voltada aos horários NGS. Os corpos de resposta TACOM não são incluídos no cache/artifact público do Actions. Para conservar evidências brutas e histórico municipal, executar em disco persistente e fazer backup de `var/gobus/source-history/` e `var/gobus/published-history/`.

A publicação é incremental por `shape_id`/`stop_id`: a ausência em uma amostra posterior não remove automaticamente a geometria anterior. Cada registro conserva sua data; não se renova artificialmente o horário de obtenção. Revisões anteriores ficam arquivadas por hash. Remoções ou alterações de vigência exigem evidência específica.

## Testes e limites

Regressões verificam Viamão dentro do envelope antigo e fora da área de Canoas, parsing do recurso individual, descoberta sem adivinhar itinerários, exclusão de pontos externos, preservação de estado não homologado, ausência de IDs de veículos nos produtos publicados, seleção e filtros de paradas. Resultado local desta revisão: **111 testes Python e 25 TypeScript/React**, lint e build aprovados. O estado da publicação deve ser conferido no run do commit final.

QA visual verificou desenho simultâneo de 5000/5001, enquadramento, filtro de paradas por linha e popup da parada 7844. Exportação CSV filtrada foi baixada e conferida. O teste móvel é viewport interno de navegador, não aparelho físico. MapLibre/WebGL depende de suporte do dispositivo; o modo compatível usa Canvas/Leaflet e PMTiles.

GPS contínuo, ETA público, timestamp de medição embarcada, viagens e auditorias operacionais ainda dependem de contrato de dados, infraestrutura persistente e homologação. As novas linhas no mapa não comprovam operação atual, pontualidade ou cumprimento contratual. Uma coleta adicional planejada não foi executada porque a autorização de rede foi cancelada antes da decisão; os dados publicados decorrem das capturas concluídas anteriormente.
