# Roteiro do vídeo · PetPulse (WARNED.) · máx. 5:00

**Formato:** gravação de tela (app em `http://localhost:8000`) com narração. Opcional: rosto no canto. Antes de gravar, rode `python3 -m http.server 8000 --directory src/web` e deixe abertos o app, o terminal na pasta `src/` e o README.

| Tempo | Tela | Fala (sugestão) |
|---|---|---|
| **0:00–0:10** | Capa do PDF ou logo WARNED. | "Grupo 28, projeto PetPulse. **QUERO CONCORRER.**" |
| 0:10–0:40 | Foto ou ilustração de parque e o slide do problema (PDF, seção 1) | "Parques e cachorródromos de São Paulo recebem centenas de cães por dia, mas ninguém sabe quando estão cheios, quantos trancos acontecem nas guias, nem como a prefeitura deveria dimensionar esses espaços. Os apps atuais dependem de check-in manual." |
| 0:40–1:05 | Artboard CLIP-01 no Claude Design | "O CLIP-01 é um sensor de coleira com ESP32: célula de carga para a força na guia e barômetro + IMU para a altura do cão, o eixo Z. Z é a elevação do sensor menos a cota do terreno da Google, vezes cem. Sem nenhum clique do tutor." |
| 1:05–1:35 | Terminal: `python3 -m petpulse.pipeline` e `python3 -m pytest -q tests` | "Todos os dados desta POC são simulados, com semente fixa: 600 cães e 36 mil leituras. O pipeline indexa em hexágonos H3 resolução 10, agrupa com DBSCAN em uma janela de 15 minutos e grava no SQLite. São 20 testes passando." |
| 1:35–2:05 | Gráficos da EDA (`docs/img`) e tabela de sensibilidade do ε | "Na análise exploratória vemos o pico às 18h, 14% das leituras na faixa de tranco e o eixo Z separando bem os portes. Escolhemos ε de 45 metros: menos que isso fragmenta, mais que isso funde parques vizinhos." |
| 2:05–3:20 | **App ao vivo**: clicar Ibirapuera → painel; `PICO 18H`; `PUXADA +15KGF` (CLIP-01 sobe); `SALTO 3D`; `EIXO Z` on/off; `3D 45°` | "No mapa 3D, cada hexágono é uma zona pública; a altura é o índice DBM, uma métrica nossa em escala logarítmica, que não é o dBm de rádio. O painel mostra tração média, pico, faixas de guia e estatura. Simulo o pico das 18h... e uma puxada de 15 kgf: o CLIP-01 do Thor reage na hora." |
| 3:20–3:50 | Slider `DBSCAN ≥ N` de 3 para 6 e contador "ocultos (LGPD)" | "Privacidade por padrão: só aparecem grupos com pelo menos N cães. Isolados ficam ocultos, nenhum ID sai do backend e a janela é de 15 minutos. Subindo o N, mais zonas somem: é a k-anonymity em ação." |
| 3:50–4:10 | `REPLAY DIA (PYTHON)`, slider até 18:00, e `VER A` | "Este replay usa os clusters gerados pelo pipeline Python: a mesma lógica nas duas linguagens, com testes de paridade." |
| 4:10–4:35 | Tabela de integração (README) | "Integramos análise exploratória, agrupamento, visualização espacial, banco relacional, ESP32, cibersegurança e APIs de nuvem." |
| 4:35–4:55 | ODS (PDF, seção 4) e limitações | "Contribuímos com o ODS 11.7, espaços públicos seguros, e o ODS 3, prevenção de quedas e saúde. Limitações: não há hardware em campo, e o eixo Z real exigiria calibração diferencial. Próximo passo: um piloto no Ibirapuera." |
| 4:55–5:00 | Logo | "PetPulse: o parque sabe, sem ninguém precisar contar. Obrigado!" |

**Checklist de publicação**
- [ ] Duração ≤ 5:00
- [ ] "QUERO CONCORRER" dito nos primeiros segundos, junto com o nome do grupo
- [ ] YouTube → Visibilidade: **Não listado**
- [ ] Link colado no PDF (seção 6) e no README
