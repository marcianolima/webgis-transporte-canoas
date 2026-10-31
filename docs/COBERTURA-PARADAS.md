# Expansão territorial das paradas — 0.4.0, 31/10/2026

## Diagnóstico e resultado

A falta de pontos em várias regiões era principalmente uma lacuna da amostragem anterior: **385 IDs georreferenciados para 1.433 IDs conhecidos** nas listas de 72 linhas com correspondência exata de código TACOM/NGS. A consulta anterior usava até 32 locais de proximidade, concentrados em células censitárias, e poucos detalhes individuais. Isso não cobria todo o território.

A revisão publica **1.410 paradas de referência**, mais **1.025**, conservando todos os 385 IDs e os 1.386 vínculos parada–linha anteriores. Os **57 itinerários de 36 linhas** foram preservados integralmente. Não foram inferidos percursos nem pontos por endereço.

Dos 1.433 IDs das listas consultadas, **98,39% têm posição válida publicada**; os outros **23 retornaram coordenadas fora da área de referência**. Não restaram IDs pendentes de consulta nesse recorte. Isso **não equivale a 98,39% do cadastro municipal ou da população atendida**: há 81 IDs de linha NGS, 72 listas TACOM correspondentes e outras linhas históricas/códigos ainda sem conciliação. Atualidade, sentidos e vigência operacional continuam sujeitos a homologação.

## Método de aquisição

- Confirmar praça `MPA`, Canoas como `codcid=4` e códigos de linha exatos; consultar as listas de IDs por linha, sem filtrar apenas linhas programadas para o sábado.
- Distribuir **308 locais de consulta em uma grade de 700 m**, calculada em EPSG:31982 sobre a união dos bairros oficiais. Centros de células são locais de busca na API, **não paradas estimadas**. Na borda, o local de consulta é aproximado da interseção real da célula com a base territorial.
- O serviço de proximidade apresentou raio máximo observado de aproximadamente 500 m. A grade amplia a busca espacial; não é garantia de completude do serviço. Cruzar cada ponto retornado com os IDs das listas municipais e validar sua posição contra a área de referência.
- Consultar `buscarDadosParada` exclusivamente com IDs efetivamente observados nas listas para resolver as lacunas restantes. Não enumerar IDs possíveis.
- Reutilizar posições publicadas com proveniência e horário original. Não atualizar artificialmente a data de obtenção ao reprocessar.
- Manter fora do mapa os pontos incompatíveis com a referência: união dos bairros com buffer de 250 m. Essa união não é limite municipal homologado; os 23 casos precisam de revisão territorial e do fornecedor, sem classificação automática de irregularidade.

Duas execuções, até dois leitores simultâneos, intervalo global de 2 s, timeout de 60 s e orçamento de 300 requisições por execução: **386 respostas HTTP válidas**, **416 usos de cache**, nenhuma falha e nenhuma nova tentativa necessária. Não houve consulta de GPS ou novas previsões nesta expansão.

```bash
PYTHONPATH=pipeline .venv/bin/python -m transporte.gobus_geography \
  --authorized --allow-plain-http --max-requests 300 \
  --grid-spacing 700 --geo-samples 260 --detail-limit 30 \
  --prediction-samples 0 --interval 2 --timeout 60 --retries 2
PYTHONPATH=pipeline .venv/bin/python -m transporte.publish_geography
# Depois da primeira publicação local validada, completar a grade e os IDs restantes:
PYTHONPATH=pipeline .venv/bin/python -m transporte.gobus_geography \
  --authorized --allow-plain-http --max-requests 300 \
  --grid-spacing 700 --geo-samples 320 --detail-limit 220 \
  --prediction-samples 0 --interval 2 --timeout 60 --retries 2
PYTHONPATH=pipeline .venv/bin/python -m transporte.publish_geography
PYTHONPATH=pipeline .venv/bin/python scripts/prepare_catalogue.py
PYTHONPATH=pipeline .venv/bin/python scripts/validate_public.py
```

Os números de consultas reais dependem do cache e da publicação disponível. O limite total inclui retries. Em ambiente novo, a primeira rodada pode esgotar o orçamento antes do plano; revisar o resultado parcial, preservar o diretório privado e retomar sem apagar o cache. Os controles de suspensão por autorização, limite de tráfego e falhas transitórias continuam ativos.

## Resultado por bairro

Contagens por ID, com atribuição única pela geometria original. Área próxima usa buffer euclidiano de 300 m em EPSG:31982; não corresponde a caminhada, frequência ou população atendida.

| Bairro | Antes | Agora | Área até 300 m (%) |
| --- | ---: | ---: | ---: |
| Brigadeira | 4 | 29 | 24,5 |
| Centro | 23 | 77 | 100,0 |
| Estância Velha | 73 | 123 | 93,5 |
| Fátima | 37 | 85 | 71,7 |
| Guajuviras | 36 | 115 | 50,4 |
| Harmonia | 45 | 133 | 99,4 |
| Igara | 20 | 114 | 96,4 |
| Ilhas das Garças | 0 | 0 | 0,0 |
| Industrial | 1 | 23 | 14,1 |
| Marechal Rondon | 18 | 60 | 74,4 |
| Mathias Velho | 15 | 97 | 85,2 |
| Mato Grande | 19 | 83 | 35,7 |
| Niterói | 14 | 119 | 72,6 |
| Nossa Senhora das Graças | 17 | 84 | 37,9 |
| Olaria | 41 | 72 | 93,5 |
| Rio Branco | 15 | 86 | 88,7 |
| São José | 6 | 78 | 75,3 |
| São Luís | 1 | 31 | 17,9 |

Um ponto publicado fica na faixa de borda, sem bairro atribuído. Três pontos incidem em bordas/sobreposições de mais de um bairro: o primeiro polígono na ordem estável da fonte define o bairro principal. A densidade usa esse vínculo único; a soma dos bairros mais o ponto sem bairro confere com os 1.410 IDs. Essa regra corrige a dupla contagem observada durante a expansão e não homologa a delimitação administrativa.

## Produtos e interface

- `public/data/stops.geojson`: posições reais, vínculos, sentido de origem quando informado, fonte, SHA-256, hora e estado de referência.
- `public/data/stop-inventory.json`: todos os IDs conhecidos, situação de localização, fonte das listas e completude por linha. IDs excluídos permanecem identificáveis, sem coordenada estimada.
- `public/data/territory.json`: densidade, área próxima e qualidade de atribuição dos bairros.
- `public/data/transporte-canoas.pmtiles`: **826.541 bytes**, 28 tiles, 18 bairros, 659 setores, contorno derivado, 57 itinerários e 1.410 paradas. SHA-256 `a2462afe18808972a98c88a00f1e33b18b075dc3e84f32bf866bf95c422418aa`.
- Tela de paradas: completude, tabela por linha, motivos de exclusão, CSV por linha e exportação dos IDs sem posição no mapa.
- Mapa: contagem das paradas efetivamente visíveis, filtros de bairro/busca/linha aplicados também nos tiles PMTiles e explicação do filtro; novos temas de paradas/km² e percentual de área até 300 m, com unidades, legenda e ausência de dados explícitas. Mesmos indicadores no modo compatível, na alternativa GeoJSON e no MapLibre.

Fórmula de localização no recorte: `100 × IDs conhecidos com posição publicada / IDs únicos das listas consultadas`. A soma dos vínculos por linha pode superar o total de IDs, pois uma parada atende várias linhas. IDs podem representar sentidos ou plataformas; não foram fundidos por proximidade.

## Preservação, privacidade e validação

Checkpoint anterior à expansão, histórico de respostas e journals privados foram mantidos. A cópia privada recuperável foi atualizada com **1.203 arquivos**, com integridade por entrada verificada, conservando o histórico de versão. Respostas brutas e identificadores de veículos não são publicados no GitHub. A origem TACOM continua HTTP legado; não há autenticação TLS da integridade da resposta.

Validação local: **128 testes Python e 30 TypeScript/React**, lint, build, contagens, IDs/vínculos preservados, geometria, hashes e dados públicos aprovados. Evidências em `research/stop-coverage-2026-10-31.json`. Publicação verificada no commit `29e4f037f3ec8416e8a988f1d8f9b5444dd7f4fa`, [run 41216297572](https://github.com/marcianolima/webgis-transporte-canoas/actions/runs/41216297572), com build/deploy aprovados. Navegador público confirmou 1.410 marcadores e o tema de densidade. Binário público e leitura Range HTTP 206 conferem com o SHA-256 do manifesto. GPS contínuo, ETA, equivalência de horários e inventário municipal completo permanecem pendentes de homologação.
