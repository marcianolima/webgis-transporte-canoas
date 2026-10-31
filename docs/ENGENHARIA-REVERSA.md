# Engenharia reversa e validação das fontes

Data da investigação: 30/10/2026, America/Sao_Paulo. Esta documentação distingue observação direta, referência de terceiros e hipótese. Não houve contorno de autenticação, pinning, limites ou barreiras de distribuição.

## Aplicativo e versões

- Pacote Android: `com.tacom.canoas.gobus`; desenvolvedor TACOM, confirmado na [Google Play](https://play.google.com/store/apps/details?id=com.tacom.canoas.gobus).
- Na obtenção direta do HTML da loja nesta execução, a estrutura de metadados apresentou versão **1.31.3** e atualização **07/10/2026**. A indexação do mecanismo de pesquisa apresentava uma versão temporal anterior (31/01/2025); não foi tomada como comprovação de versão atual. Evidência sanitizada: `research/app-observation.json`.
- O [histórico iOS](https://apps.apple.com/gb/app/canoas-gobus/id1467359778) lista 1.31.3, 1.29.1, 1.28.0, 1.24.2, 1.24.1, 1.24.0 e versões anteriores. Histórico de iOS não comprova a arquitetura do APK Android.
- O [TEU Ônibus](https://play.google.com/store/apps/details?id=com.tacom.teuonibus) cobre várias redes municipais e metropolitanas. Não importamos suas linhas como se fossem a rede municipal de Canoas.

## APK: dependência real

Nenhum APK obtido legitimamente do dispositivo do operador ou disponibilizado diretamente pelo desenvolvedor estava acessível neste ambiente. Uma página de distribuição de terceiros respondeu 403. Não foi realizada decompilação, captura de tráfego nem comparação de requests do aplicativo. Não há resultado JADX/APKTool a declarar.

O utilitário `scripts/apk_audit.py` faz triagem **offline** do APK fornecido pelo operador: calcula SHA-256 e lista hosts e nomes de recursos sem expor parâmetros, credenciais ou copiar código proprietário. Exemplo:

```bash
adb shell pm path com.tacom.canoas.gobus
adb pull CAMINHO_RETORNADO aplicativo.apk
python scripts/apk_audit.py aplicativo.apk
jadx -d /diretorio/privado/jadx aplicativo.apk
apktool d aplicativo.apk -o /diretorio/privado/apktool
```

Os três últimos comandos pressupõem arquivo do próprio ambiente autorizado. JADX e APKTool são ferramentas externas, não instaladas ou executadas nesta sessão. Não comitar APK, dumps ou código decompilado. Localizar `pracaApp`, `json.js`, bases HTTP e bibliotecas Cordova/rede e confirmar no aparelho de teste. Arquitetura Cordova é referência da família SIU, **não fato confirmado deste APK**.

## Referência SIU Mobile

[Pesquisa e Documentação — SIU Mobile, Bruno Armanelli](https://gist.github.com/brunoarmanelli/71193578d84b929799653aa61cdb4ba9), licença indicada pelo autor: CC BY-NC-ND. Usada como referência de investigação, sem copiar seu texto ou código.

A referência descreve BHZ e menciona GOBUS e TEUONIBUS entre identificadores de praça. Contratos candidatos: `buscarLinhas`, `V3/buscarParadasProximas`, `V3/retornaVeiculosMapa`, `V3/buscarItinerario`, `retornaQroLinha`, `V3/buscarPrevisoes`, paradas por itinerário. Isso não comprova a disponibilidade em Canoas.

### Verificações conservadoras efetuadas

| Consulta | Resultado observado | Conclusão permitida |
| --- | --- | --- |
| Host BHZ, `buscarLinhas` documentado | HTTP 200, JSONP, linhas com `praca=BHZ` | Contrato legado observado em BH; dados excluídos da rede de Canoas |
| Host BHZ, `V3/buscarParadasProximas/-51.181/-29.919/0/GOBUS/retornoJSONH` | HTTP 200, sucesso e lista vazia | Resposta vazia não homologa Canoas nem o código GOBUS neste host |
| Hosts candidatos `gobus.siumobile.com.br` e `teuonibus.siumobile.com.br`, paths plausíveis | HTTP 503 neste ambiente | Hipóteses não comprovadas; não é diagnóstico de indisponibilidade global do fornecedor |
| Endpoints municipais GoBus | Nenhum com dados municipais validado | GPS, ETA, paradas e trajetos permanecem pendentes |

URLs e horários das hipóteses constam em `research/siu-probes.json`. Não foram feitas enumeração de IDs, tentativa de credenciais ou chamadas que registram uso/avisam motoristas.

## Fonte alternativa efetivamente validada: Sogal / NGS

1. [Página da Sogal](https://sogal.com.br/) aponta “Horários” para `https://ngsservicos.com/sogal/horarios/`.
2. O HTML público carregou um bundle Angular com referências explícitas aos cinco recursos descritos em `ENDPOINTS.md`.
3. Foram lidos o HTML e o JavaScript público como contratos do portal; não houve acesso a código de servidor ou área administrativa.
4. `getDataLiberada.php` retornou datas de 30/10 a 03/11/2026.
5. `getLinhas.php?DATA=2026-10-30` retornou 77 linhas, e os endpoints de horário e itinerário responderam com dados municipais.
6. `getMapaJson.php?LINHA=05000&SENTIDO=01`, identificado no bundle, respondeu 404. O mesmo recurso sem sentido também respondeu 404. Nenhum trajeto foi desenhado por aproximação.

O bundle contém referência a um provedor de mapa comercial. Nenhuma chave desse fornecedor foi incorporada, reutilizada ou publicada pelo projeto. O mapa usa MapLibre com camadas locais e OpenStreetMap como fundo opcional.

## Limites e frequência

Não foi identificado SLA ou limite formal publicado para a API NGS. Coletor: no máximo duas conexões, intervalo global mínimo de 0,75 s, cache de respostas, timeout, até duas novas tentativas com backoff; 401/403/404 interrompem a tentativa daquele recurso. Atualização estática diária, sem polling de alta frequência na NGS. Dados consultáveis publicamente não constituem licença geral sobre sistemas proprietários; créditos e URLs de origem acompanham os dados.

Frequência de origem GPS, autenticação GoBus, identificação de frota/viagem, precisão e condições de redistribuição do feed GPS continuam a confirmar. Um acordo técnico com o fornecedor ou um APK de teste é a dependência para avançar essa parte.

## Revisão 0.2.0 — geometrias ainda indisponíveis

O mapa local PMTiles resolve a publicação e o desenho de cartografia; não recupera trajetos ausentes. O endpoint de mapa observado no JavaScript NGS, `https://ngsservicos.com/sogal/scripts/getMapaJson.php?LINHA=05000&SENTIDO=01`, continuou retornando 404 no ambiente de investigação. A variante sob `aplicativos/NgPortais/sogal/scripts/` também retornou 404 e permanece hipótese rejeitada, não endpoint homologado. O diretório de serviços GeoCanoas retornou 503 neste ambiente. As buscas por feed municipal GTFS atual e consulta Overpass não forneceram geometria utilizável. Isso não demonstra ausência de dados na prefeitura ou indisponibilidade global das fontes.

Resultado objetivo: **GoBus/TACOM não teve a API operacional homologada**. Horários, cadastro e logradouros vieram do portal **Sogal/NGS**. Não houve APK legítimo disponível, decompilação, captura de tráfego ou autenticação TACOM validada. A referência SIU de BHZ/GOBUS não foi promovida a contrato de Canoas. Próxima dependência: APK legítimo ou documentação/amostra autorizada; alternativamente, GTFS/GeoJSON municipal oficial para trajetos e paradas.

A versão 0.2.0 implementa importação de geometria, preservação de fonte/hash/data, filtros, desenho e testes isolados. A base publicada de linhas geográficas permanece vazia, explicitamente pendente. Consulte [MAPA-PMTILES.md](MAPA-PMTILES.md).
