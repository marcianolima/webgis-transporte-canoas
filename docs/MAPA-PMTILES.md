# Mapa, PMTiles e importação de trajetos — 0.2.0

## Correção e limites

O mapa usa `public/data/transporte-canoas.pmtiles`, arquivo **PMTiles v3 com tiles vetoriais MVT**, produzido a partir das bases reais locais. Não é uma imagem de mapa nem um link para um serviço de terceiros. O arquivo contém 18 bairros, 659 setores censitários e um contorno derivado da união dos bairros. Zooms 8–13, com desenho vetorial ampliado nos zooms posteriores. O arquivo tem aproximadamente 263 kB; tamanho exato e SHA-256 estão em `map-manifest.json`.

A versão anterior dependia da inicialização de WebGL para depois tentar a alternativa. A nova versão inicia em **modo compatível, Leaflet + desenho Canvas 2D dos tiles vetoriais**, sem exigir WebGL, servidor de tiles, chave CARTO ou fundo OSM. Há altura explícita, observação de redimensionamento e reinicialização manual. MapLibre/WebGL continua selecionável. Erro de inicialização retorna ao modo compatível. Falha de PMTiles mantém o mapa com os GeoJSON locais e aviso visível.

Não foi possível reproduzir o dispositivo/navegador do relato original; portanto, não se atribui uma causa única ao problema reportado. Os testes confirmam o novo caminho de funcionamento no navegador de QA sem WebGL.

Leituras usam HTTP Range. Caso o servidor não aceite Range, há uma transferência completa por instância do mapa, limitada a 20 MB, com verificação da assinatura PMTiles. A URL inclui a versão do SHA do manifesto para evitar mistura de arquivos entre publicações. Reiniciar o mapa cria nova instância de leitura. Os GeoJSON completos continuam sendo as fontes para análise; simplificação/recorte dos MVT não deve ser usado para medir áreas ou desvios operacionais.

## Seleção de linhas

- Uma ou várias linhas podem ser selecionadas, buscadas e removidas no mapa.
- Cada ID tem cor estável. Havendo geometria, ela é filtrada, desenhada e enquadrada.
- A página de detalhes de linha também inclui mapa ligado à linha selecionada.
- Sem geometria, o aviso informa a pendência e o botão de enquadrar percurso fica desabilitado. Não se conectam logradouros ou terminais por segmentos inventados.
- A legenda e os popups distinguem geometria de referência e origem; importar não equivale a aprovar um trajeto autorizado.

**Nesta publicação: 0 das 81 linhas cadastradas possuem geometria importada; 0 paradas geográficas.** Os 81 cadastros e 4.990 horários são dados reais, mas não fornecem coordenadas dos percursos. O importador e o desenho foram testados com fixtures sintéticas isoladas, que não entram nos arquivos públicos.

## Gerar o PMTiles

```bash
PYTHONPATH=pipeline .venv/bin/python -m transporte.tiles
PYTHONPATH=pipeline .venv/bin/python scripts/validate_public.py
npm run build
```

O gerador transforma EPSG:4326 em Web Mercator para codificação, recorta, generaliza e quantiza os tiles, comprime com gzip e escreve o arquivo temporário antes da substituição. Registra contagem de feições, hash de cada fonte, versão do método e disponibilidade por ID de linha. O conteúdo do arquivo é determinístico para as mesmas fontes; o manifesto registra também a hora de processamento. O workflow regenera o arquivo depois da eventual atualização estática e antes dos testes/deploy.

## Importar geometria real de GeoJSON

Obter um arquivo municipal com origem e condições de uso verificadas. Não utilizar a fixture de teste como base. O arquivo deve ser FeatureCollection em EPSG:4326, com LineString/MultiLineString e propriedades `route_id` (ID ou código exato do cadastro), `shape_id` e `direction` quando conhecidos. Não são feitas associações por semelhança de nome. Coordenadas são verificadas contra o envelope operacional de validação; esse envelope não é um limite municipal oficial.

```bash
PYTHONPATH=pipeline .venv/bin/python -m transporte.import_shapes /caminho/percursos-reais.geojson \
  --format geojson \
  --source-url https://DOMINIO-DA-FONTE/ARQUIVO-REAL.geojson \
  --source-name 'Nome da fonte responsável' \
  --reference-date AAAA-MM-DD \
  --municipality-code 4304606
```

Os argumentos acima são instruções de configuração, não endereços de uma integração existente. A URL deve ser HTTPS sem credenciais. O importador não baixa arquivos nem autentica em serviços: processa o arquivo legítimo disponível localmente, preservando o hash da entrada e a hora de ingestão local em `fetched_at`.

A importação substitui o conjunto ativo de geometrias pelo conteúdo completo do arquivo fornecido. Antes disso, preserva a versão anterior, a nova versão e a entrada em `var/shape-history/`, por hash. Essa pasta precisa de disco persistente e backup no ambiente municipal; o GitHub não substitui esse histórico. O status resultante é `reference`, com fonte e data de referência, e exige conferência de vigência antes de uso fiscalizatório. Geometrias inválidas, linhas desconhecidas, arquivo vazio e coordenadas fora da área esperada são rejeitados antes de alterar a publicação.

## Importar GTFS

O ZIP deve conter `agency.txt`, `routes.txt`, `trips.txt` e `shapes.txt`. A agência municipal precisa ser selecionada explicitamente. Somente `route_short_name` com correspondência exata ao catálogo municipal é aceito; os joins trips → shape_id preservam o sentido fornecido. Redes de outras agências são excluídas. Quando `feed_info.txt` fornece início/fim, a data de referência precisa estar dentro da validade. Ausência de validade no feed não comprova atualidade. Calendários e viagens desse GTFS não substituem automaticamente a programação NGS: esta etapa importa somente geometria.

```bash
PYTHONPATH=pipeline .venv/bin/python -m transporte.import_shapes /caminho/gtfs-municipal-real.zip \
  --format gtfs --agency-id ID-MUNICIPAL-CONFERIDO \
  --source-url https://DOMINIO-DA-FONTE/GTFS-REAL.zip \
  --source-name 'Publicador do GTFS municipal' \
  --reference-date AAAA-MM-DD --municipality-code 4304606
```

Não foi localizado e validado um GTFS atual de Canoas nesta execução. Não se declara esse adaptador homologado com um feed real de produção. Antes de publicar: conferir origem, agência, código de linha, sentido, vigência, permissões, diff dos arquivos, testes e desenho cartográfico. Depois da importação o próprio comando regenera PMTiles/manifesto.

## Verificação

Testes automatizados cobrem cabeçalho/hash/camadas do arquivo real, integridade de fontes, tile de Canoas, orientação dos eixos MVT, determinismo, seleção/enquadramento, consulta espacial com buracos, Range, servidor sem Range, cancelamento, limite de tamanho e rejeições do importador. O QA visual confirmou bairros/setores, seleção de bairro, desenho e limpeza de linha em fixture isolada, fallback GeoJSON e viewport móvel. Não foi homologado MapLibre/WebGL neste navegador, que não disponibiliza WebGL.

Referências técnicas: [PMTiles com MapLibre](https://docs.protomaps.com/pmtiles/maplibre) e [PMTiles com Leaflet](https://docs.protomaps.com/pmtiles/leaflet). O modo compatível implementa o desenho dos MVT diretamente, sem depender do renderizador protomaps-leaflet em manutenção.
