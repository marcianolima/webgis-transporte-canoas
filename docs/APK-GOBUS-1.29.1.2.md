# Engenharia reversa estática — APK Canoas GoBus 1.29.1.2

Análise realizada em 30/10/2026 do arquivo fornecido pelo operador da conversa, **sem executar o APK, efetuar login, interceptar tráfego ou consultar endpoints de escrita**.

## Evidência e escopo

- Artefato analisado: `CANOAS+GoBus_1.29.1.2_APKPure.apk`, SHA-256 `6c9fa124cc8dfa7da78076676d3f580fd60a3201e0f6a70e503ac3b43bc01c1f`.
- Arquivo Android ZIP válido: **691 entradas**; apenas `classes.dex` (~5,9 MB) e aplicação Cordova em `assets/www/`.
- Identificação no JS: `pracaApp="GOBUS"`, `nomePraca="Canoas"`, `siumobileVersao="1.29.1.2"`, `idAplicativoConfigXml="com.tacom.canoas.gobus"`.
- O aplicativo inclui `json.js`, `mapa.js`, `previsao.js`, `sublinhasDaLinha.js`, HTML das telas e bibliotecas Leaflet/jQuery. A camada de mapas usada no APK é **Leaflet**, não PMTiles. O projeto municipal mantém PMTiles no frontend próprio.
- URL principal explicitamente atribuída em `assets/www/js/json.js` linha 17:
  `http://mpa.siumobile.com.br:6060/siumobile-ws-v01/rest/ws/`.
  Comentário de desenvolvedor: Porto Alegre. **Host/endereço configurado no pacote e posteriormente confirmado respondendo a endpoints de leitura nos runners do GitHub Actions.**
- Requisições `$.ajax` são GET, `dataType:'jsonp'`, timeout 45 s; o callback costuma ser o último segmento do caminho. Ao construir JSONP, o jQuery pode acrescentar parâmetro query de callback: teste real é necessário antes de implementar cliente de produção.
- `ccUsr` passa a ser `0` pela função `pegaCodUsr()`, mas isso **não equivale a autorização pública formal**.
- `pracaApp=GOBUS` (identidade da versão do app) **não é o mesmo parâmetro** que `siuMobileCidade`. O estilo cita `CAN`, porém o host principal responde sob a praça `MPA`; o serviço `V3/cidadesLinhas/MPA` confirmou **Canoas como `codcid=4`**. `cidadesApp` retornou lista vazia nessa origem. O identificador `codcid` deve ser validado e utilizado para filtrar o cadastro geral.
- O APK não contém um banco completo de itinerários ou GPS. `assets/www/praca/GOBUS/linhas.txt` guarda um **recorte local de 19 variantes metropolitanas TM1/TM2/TM3 (M101/M102/M103)**, não uma base municipal atual e não georreferenciada.

## Catálogo de recursos identificados diretamente no código

Os caminhos abaixo são relativos à URL configurada. `{cidade}` deve vir do cadastro retornado pelo servidor; `0` corresponde a `ccUsr`. São **contratos inferidos do código do cliente**, não endpoints homologados para produção.

| Recurso de leitura | Caminho observado | Estrutura consumida pelo aplicativo |
| --- | --- | --- |
| Cidades | `cidadesApp/retornoJSONCidades` | `cidade`, `sg`, `desc` (conteúdo JSON legado aninhado) |
| Linhas | `buscarLinhas/retornoJSONListaLinhas` | `linhas` (string de lista), cada `cod`, `sgl`, `nom`; alguns registros: `codcid`, `praca` |
| Sublinha | `V3/retornaSublinhasDaLinha/{codLinha}/0/{cidade}/retornoSublinhasJSON` | `subLinhas[].cod/sgl/nom` |
| Paradas de linha | `V3/buscarParadasPorLinha/{codLinha}/0/{cidade}/retornoJSON` | `paradas[].cod/end/siu/sent/temVeic` |
| Paradas com coordenadas | `V3/buscarParadasPorLinhaComCoordenadas/{codLinha}/0/{cidade}/retornoJSONH` | `paradas[].cod/x/y/desc/siu/azimute` |
| Itinerário geográfico | `V3/buscarItinerario/{codItinerario}/0/{cidade}/retornoJSONItinerario` | `itinerarios[].coordX/coordY` |
| Veículos de itinerário | `V3/retornaVeiculosMapa/{codItinerario}/0/{cidade}/retornoJSONVeiculos` | `veiculos[].numVeicGestor/lat/long/descricao/cod/direcao/cor` |
| Previsão em parada | `V3/buscarPrevisoes/{codParada}/{true` ou `false}/0/{cidade}/retornoJSON` | `previsoes[].sgLin/prev/numVeicGestor/codItinerario/tpAcess`, `horaConsulta` |
| Horários | `V3/retornaQroLinha/{codLinha}/0/{cidade}/retornoJSON` | `qros[].origem/tipoDia/horario` |
| Paradas próximas | `V3/buscarParadasProximas/{longitude}/{latitude}/0/{cidade}/retornoJSONH` | `paradas[].x/y/cod/siu/desc` |
| Linhas por parada | `retornaLinhasQueAtendemParada/{codParada}/0/retornoJSON` | `linhas` e atributos de linha, a confirmar |
| Sequência das paradas | `buscarParadasPorItiComSequencia/{codItinerario}/{numeroVeiculo}/retornoJSONTodasParadas` | `paradas[].cod/x/y/sequencia` |

Fonte das chamadas: `assets/www/pesquisaLinha.html`, `retornaParadas.html`, `retornaQroLinha.html`, `js/mapa.js`, `js/previsao.js`, `js/sublinhasDaLinha.js`, `js/mapa-embarquei.js`.

### Geometria de itinerário: solução para o mapa

A função `retornoJSONItinerario` em `assets/www/js/mapa.js` (linhas 771–797) itera `data.itinerarios`, trata `coordY` como latitude e `coordX` como longitude, preserva a ordem dos vértices e desenha uma *polyline*. Para o WebGIS, um itinerário homologado é um `GeoJSON Feature` `LineString` com pares `[longitude, latitude]` em EPSG:4326, identificador do **itinerário** e vínculo verificado ao código e sentido da linha. Em seguida, o arquivo pode ser convertido a PMTiles/MVT, mantendo variações e vigência. **Não converter lista textual NGS em geometria aproximada.**

O ID `codItinerario` pode aparecer nas previsões; isso **não garante** cobertura de itinerários sem ônibus ativo. É necessário descobrir o vínculo estável *linha → sublinha/sentido → itinerário* para converter todas as 81 IDs NGS publicadas. As duas fontes podem usar códigos incompatíveis; relacionar por nome é somente hipótese e exige revisão humana.

### Telemetria, ETA e auditoria

- O aplicativo consulta `retornaVeiculosMapa` por `codItinerario` com intervalo nominal de **6 segundos**, em `assets/www/js/mapa.js` linha 11. Isso descreve o comportamento do cliente original e **não é recomendação de frequência de coleta municipal**.
- O objeto de veículo fornece coordenadas, identificação e direção. **Não há campo de timestamp de GPS comprovado no processamento da tela**. Horário de coleta HTTP não deve ser tratado como hora de medição embarcada.
- O próprio aplicativo usa `buscarPrevisoes` para ETA por parada e `buscarParadasPorItiComSequencia` para ordenamento de pontos.
- Isso habilita tecnicamente mapas de posições recentes e previsões, **mas não permite afirmar pontualidade, viagem realizada, infração, atraso GPS ou SLA de origem** sem histórico, timestamps e serviço validado.

### Operações excluídas da integração

O código também contém consultas envolvendo cartão PNE e operações como `emiteAvisoMotorista`, `emiteAlarmeDesembarquePNE`, `emiteAlarmePanico` e `registraUsoSistema`. Mesmo quando usam GET, podem produzir efeitos no servidor ou processar identificadores pessoais. **Não foram executadas nem incluídas no adaptador.**

## Validação, segurança e implantação

1. **Análise estática concluída:** parâmetros, caminhos e formato esperado foram observados diretamente no APK e documentados. Scripts PHP/Python externos e comportamento dos servidores não foram analisados.
2. **Testes de leitura online concluídos para catálogo, paradas e previsões:** runners autorizados do GitHub Actions receberam respostas JSONP do host MPA. `cidadesApp` retornou lista vazia; `buscarLinhas` apresentou **1.070 linhas** da praça MPA, em **14 `codcid` distintos**; `V3/cidadesLinhas/MPA` confirmou `CANOAS=4`. Filtrando `codcid=4`, foram identificados **204 registros TACOM**; 72 com códigos coincidentes candidatos aos 81 IDs distintos do NGS. Essas coincidências exigem revisão de sentidos e variantes.
3. **Amostra geográfica real:** para linha `05006`, `V3/buscarParadasPorLinhaComCoordenadas` retornou **64 paradas com coordenadas locais**; a consulta pontual `buscarPrevisoes` retornou sete previsões, nenhuma com vínculo confirmado de itinerário à linha testada. **Nenhum GPS ou itinerário linear completo foi publicado**; os dados reais obtidos nesses testes não foram inseridos na cartografia pública, que continua pendente de homologação.
4. Há um risco de integridade/confidencialidade porque a base do APK é **HTTP**, não HTTPS. Para produção, exigir canal seguro, termos de uso e autorização de redistribuição/consulta com TACOM/operadora. Nunca embutir tokens, dados PNE, cartões ou GPS bruto em GitHub Pages.
5. O projeto passa a ter `pipeline/transporte/gobus.py`, que permite montar **somente caminhos de leitura**, analisar JSONP sem executá-lo, validar coordenadas e gerar GeoJSON de itinerários **marcado não homologado**. Há testes offline em `tests/test_gobus.py`. O worker GPS existente continua corretamente bloqueado até `SOURCE_HOMOLOGATED=true` e um feed HTTPS autorizado.
6. Para liberar a integração: usar a relação confirmada `MPA/codcid=4` como filtro, validar correspondência SIU↔NGS e itinerários/sentidos, acordar direitos de publicação e coleta, obter os trajetos reais com vigência, confirmar timestamp GPS e limites, implantar proxy/API segura e só então produzir PMTiles reais. Ver [homologação GoBus](GOBUS-HOMOLOGACAO.md).

**Limite decisivo:** descobrir a API do aplicativo **não é o mesmo que ter os dados operacionais**. O aplicativo 1.29.1.2 é anterior à versão 1.31.3 observada na loja; requer validação de eventuais alterações de backend.

## Como realizar a homologação manual com a operadora

Há um verificador **opt-in de uma única requisição**, fora da rotina de CI e sem envio de registros ao GitHub: `scripts/verify_gobus_endpoint.py`. Ele exige declaração explícita de autorização e, como o APK usa HTTP, reconhecimento do risco de transporte sem TLS. Respostas são armazenadas em `var/gobus/`, excluído da publicação.

```bash
# Executar apenas de rede/autorização compatíveis com as condições do serviço:
PYTHONPATH=pipeline python scripts/verify_gobus_endpoint.py cidades --autorizado --permitir-http
PYTHONPATH=pipeline python scripts/verify_gobus_endpoint.py linhas --autorizado --permitir-http
# Só depois de identificar a cidade e um itinerário real pela fonte:
PYTHONPATH=pipeline python scripts/verify_gobus_endpoint.py itinerario --itinerario 123 --cidade CAN --autorizado --permitir-http
# Exemplo de conversão local de um payload já capturado:
PYTHONPATH=pipeline python scripts/gobus_extract.py itinerario var/gobus/ARQUIVO.jsonp --itinerario-id 123 > var/gobus/itinerario-123.geojson
```

`123` e `CAN` no exemplo **não são valores homologados**; substituir apenas após validar o cadastro de cidade e o código real. Não criar agendamento de polling, não executar recursos que emitem avisos ou alarmes e não publicar respostas brutas sem avaliação de origem, segurança, finalidade e licenciamento.
