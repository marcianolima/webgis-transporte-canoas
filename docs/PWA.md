# WebGIS Transporte Canoas como PWA

A aplicação é instalável no Android e em navegadores compatíveis em HTTPS, sem APK ou loja. O deploy continua no GitHub Pages, no caminho `/webgis-transporte-canoas/`. A instalação **não cria uma fonte de GPS** e não altera as permissões da TACOM.

## Instalação

- Android / Chrome ou Edge: abrir a aplicação pelo HTTPS, escolher **Instalar aplicativo** quando o navegador disponibilizar o convite. Também é possível pelo menu do navegador > Instalar app/Adicionar à tela inicial.
- iOS / Safari: abrir no Safari, tocar em **Compartilhar** > **Adicionar à Tela de Início**; em iOS compatível a PWA abre sem interface do Safari.
- Desktop: instalar pelo ícone do navegador ou pelo botão **Instalar** da aplicação, quando ofertado.

O botão do cabeçalho pode apresentar instruções quando o navegador não autoriza o prompt. A instalação depende do navegador, do modo de navegação, da segurança HTTPS e de critérios próprios da plataforma.

## Offline: escopo e limite

- O service worker tem escopo exclusivamente dentro do projeto, não intercepta outros sites nem requisições de terceiros.
- Recursos estáticos e chunks JS/CSS do build são pré-armazenados. Apenas as referências públicas `data/*.json` e `data/*.geojson` **exceto `data/vehicles.json`** podem ser reutilizadas offline **depois de consultadas**.
- Respostas de API/veículos/GPS/ETA, credenciais e solicitações não GET nunca entram no cache. Arquivos **PMTiles e Range** não são interceptados, para não invalidar requisições parciais. O mapa poderá usar arquivos GeoJSON anteriormente consultados, conforme suporte de cada motor cartográfico.
- Sem conectividade, há aviso explícito de que horários/cartografia são cópias de referência, potencialmente desatualizadas, **não operação em tempo real**. Dados ainda não consultados não estarão disponíveis.
- O navegador pode limpar o armazenamento offline a qualquer momento; não há garantia de persistência permanente.
- Atualizações do WebGIS aparecem como ação explícita **Atualizar aplicativo**; sem recarga automática que interrompa o usuário.

## Desenvolvimento e testes

`npm ci && npm test && npm run lint && npm run build && npm run test:pwa`

O `prebuild` gera os ícones PNG 192/512 via Node, sem dependências extras. O `postbuild` coleta chunks Vite publicados no `dist/assets` e escreve sua lista de precache no `dist/sw.js` com hash para atualização. Rodar em `http://localhost` para desenvolvimento; validar instalação/atualização em HTTPS publicado. No modo dev o service worker não é registrado.

### Checklist de aceitação no celular

1. Primeira visita online, conferir manifesto, ícones, botão de instalação, tema e navegação inferior.
2. Instalar no Android/iOS e conferir standalone, retorno à página e safe area.
3. Abrir mapa, linhas e paradas; ativar modo avião e testar referências acessadas, verificando aviso offline. O GPS não pode aparecer como atual.
4. Atualizar build no Pages; ao voltar ao app aceitar atualização e verificar nova versão.
5. Validar que PMTiles com `Range` não é interceptado e que a API HTTPS não é armazenada.
