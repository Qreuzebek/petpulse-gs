# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href="https://www.fiap.com.br/">
  <img src="../../assets/logo-fiap.png" 
       alt="FIAP - Faculdade de Informática e Administração Paulista" 
       width="40%">
</a>
</p>

<br>

# PetPulse · WARNED. — Inteligência geográfica canina passiva para espaços públicos

## Grupo 28

## 👨‍🎓 Integrantes: 
- <a href="https://github.com/Qreuzebek">Henrique Abreu</a> · RM 572248

## 👩‍🏫 Professores:

### Tutor(a)
- <a href="https://github.com/fiap-tutoria">Tutoria FIAP</a>
  
### Coordenador(a)
- <a href="https://www.linkedin.com/in/andregodoichiovato/">André Godoi Chiovato</a>

## 📜 Descrição

**Global Solution 2026.2 · CitizenTech — tecnologia centrada no cidadão.**

Parques, praças e cachorródromos de São Paulo recebem centenas de cães por dia, mas ninguém sabe **quando** e **onde** esses espaços ficam cheios, quantos trancos fortes acontecem nas guias (risco de queda para tutores, sobretudo idosos e crianças) ou como dimensionar a manutenção. Hoje a informação depende de relatos manuais, raros e subjetivos.

O **PetPulse (WARNED.)** é uma prova de conceito de um "Waze canino passivo":

1. O **CLIP-01 · TAG 3D** (ESP32 + célula de carga HX711 + IMU MPU6050 + barômetro) mede a **força na guia** em kgf/N e a **altura do cão no eixo Z** (`Z_cão = (Elev_sensor − GoogleElev(lat,lng)) × 100`), sem nenhum check-in manual (*geofence zero-click*).
2. As posições são indexadas em hexágonos **Uber H3 resolução 10** (~15 mil m² por célula) e agrupadas com **DBSCAN** (métrica haversine, ε = 45 m) numa janela deslizante de **15 minutos (TTL)**.
3. **Privacidade por padrão (LGPD):** só saem do backend clusters com **k ≥ N cães** (k-anonymity, padrão N = 3). Cães isolados e grupos pequenos ficam ocultos; nenhum identificador individual é publicado.
4. Cada zona recebe o **Índice DBM** (Densidade·Biomecânica·Movimento), uma métrica própria em escala logarítmica de 0 a 100. **Não é o dBm de radiofrequência**: `DBM = 100·log10(1+I)/log10(1+I_ref)`, com `I = n_cães × tração_média(kgf) × amplitude_Z(m)`.
5. O mapa 3D (Google Maps **WebGLOverlayView** via deck.gl `GoogleMapsOverlay`) mostra hexágonos extrudados pelo DBM, colunas do eixo Z e um painel neutro ("Clima comportamental": régua contínua TRANQUILA ↔ AGITADA, sem rótulos punitivos).

**Público beneficiado:** tutores urbanos (previsibilidade antes do passeio), pedestres e frequentadores dos parques, e **poder público** (dados agregados para dimensionar cachorródromos, horários de limpeza e sinalização).
**ODS:** 11.7 (espaços públicos seguros, inclusivos e acessíveis) e 3 (saúde e bem-estar: atividade física e prevenção de quedas e mordidas).

> ⚠️ **Regra 8 · transparência:** todos os cães, leituras e cenários (`+12 PETS`, `PICO 18H`, `PUXADA +15KGF`, `SALTO 3D`, perfil `THOR #8695`) são **dados simulados** de demonstração. Os locais e coordenadas são reais. As cotas de terreno são valores de referência, ou vêm da Google Elevation API quando há chave configurada. O firmware foi **compilado** para ESP32, mas não foi testado em hardware físico em campo.

### Integração entre disciplinas

| Disciplina / conteúdo | Onde está no projeto |
|---|---|
| Análise exploratória de dados | `src/petpulse/eda.py`, `notebooks/petpulse_eda.ipynb`, gráficos em `docs/img/` |
| Machine Learning · agrupamento | DBSCAN (scikit-learn, haversine) em `src/petpulse/clustering.py`, com paridade JS em `src/web/petpulse-core.js` |
| Visualização interativa / espacial | App web com mapa 3D, H3, WebGL (`src/web/`) |
| Banco de dados relacional | SQLite com 4 tabelas, CHECK constraints e índice H3+ts (`src/petpulse/db.py`) |
| Sensores, IoT e ESP32 | Firmware CLIP-01 (`src/firmware/clip01/`), simulável no Wokwi |
| Cibersegurança e privacidade | k-anonymity, TTL de 15 min, chave de API fora do Git, testes de não exposição de IDs |
| Serviços em nuvem / APIs | Google Maps JS API e Google Elevation API com cache por célula H3 |
| Programação (fases anteriores) | Python (pipeline, testes pytest) e JavaScript |

## 📁 Estrutura de pastas 

* **`data/`** Base simulada (`telemetria_simulada.csv`, `dogs_simulados.csv`), banco `petpulse.db` (gerado) e resumos da EDA.
* **`docs/`** PDF de entrega, roteiro do vídeo e imagens (`docs/img/`).
* **`notebooks/`** `petpulse_eda.ipynb`: análise exploratória e validação do DBSCAN.
* **`src/petpulse/`** Pacote Python: simulação, física (kgf/N, eixo Z, DBM), elevação com cache H3, DBSCAN + k-anonymity, SQLite e pipeline.
* **`src/web/`** App web (HTML/CSS/JS): mapa 3D, CLIP-01, painel da zona, replay do dia gerado pelo Python.
* **`src/firmware/clip01/`** Firmware ESP32 (`.ino`) e `diagram.json` do Wokwi.
* **`src/tests/`** 20 testes automatizados (pytest). Os testes do núcleo JS ficam em `src/web/test-core.mjs`.

## 📎 Links e Observações

### 🔗 Links do Projeto

* **[Vídeo de entrega no YouTube (não listado)](https://youtu.be/l8rQs4pqZ_E)**: demonstração de até 5 minutos.
* **[Deck executivo (PDF)](docs/PetPulse_Deck_GS2026-2.pdf)**: apresentação usada no vídeo.
* **[Repositório GitHub](https://github.com/Qreuzebek/petpulse-gs)**: público, com a conta `fiap-tutoria` como colaboradora.

### 🧠 Decisões Técnicas

> **H3 res-10** dá células de ~66 m de aresta, do tamanho de um cachorródromo; é mais fino que um bairro e mais grosso que um GPS individual (ajuda na privacidade).
> **DBSCAN** dispensa definir o número de grupos e trata isolados como ruído, que é exatamente o que precisamos ocultar. A métrica haversine e o ε em metros evitam distorção de lat/lng.
> **k-anonymity (min_samples = N)** usa o mesmo parâmetro como regra de clusterização e de privacidade: o slider `DBSCAN ≥ N` muda as duas coisas ao mesmo tempo.
> **Escala logarítmica (DBM)** evita que um parque lotado sature a régua e esconda diferenças entre zonas médias.
> **SQLite** porque é relacional, sem servidor e reprodutível pelo avaliador. O esquema está pronto para PostgreSQL/PostGIS.
> **Google Maps + deck.gl:** com chave, o mapa usa Google Maps vetorial + `GoogleMapsOverlay` (interleaved = WebGLOverlayView) + Elevation API. Sem chave, as **mesmas camadas** rodam em deck.gl standalone (tiles Esri/OSM), para que a demo nunca dependa de cobrança.
> **Uso de IA:** desenvolvido com apoio de assistente de IA (Claude, da Anthropic) na escrita de código, documentação e identidade visual. As decisões de escopo, a revisão e os testes foram feitos pelo integrante.
> **Duas implementações do núcleo** (Python e JS) com testes de paridade: o Python gera o histórico e o banco, e o JS roda a simulação ao vivo no navegador.

### 📢 Observações Gerais

* **Participação na Competição:** [x] Sim, aceitamos participar / [ ] Não vamos participar.
* *Outras observações:* projeto desenvolvido individualmente (Grupo 28, 1 integrante).

## 🔧 Como executar o código

Pré-requisitos: Python 3.11+, Node 18+ (opcional, para os testes JS), navegador moderno. Opcionais: chave Google Maps, arduino-cli/Wokwi.

```bash
cd 1TIAO/GLOBAL-SOLUTION-2
python3 -m pip install -r requirements.txt

# 1) gera a base simulada, o banco SQLite e os snapshots do mapa
cd src && python3 -m petpulse.pipeline

# 2) análise exploratória (gráficos em docs/img, resumo em data/)
python3 -m petpulse.eda

# 3) testes
python3 -m pytest -q tests
node web/test-core.mjs

# 4) app web: abra http://localhost:8000
python3 -m http.server 8000 --directory web
```

**Google Maps (opcional):** copie `src/web/config.example.js` para `src/web/config.js` e preencha `googleMapsApiKey` (com Maps JavaScript API e Elevation API ativas) e, se quiser, um `mapId` vetorial. Para o pipeline Python consultar a Elevation API, exporte `GOOGLE_MAPS_API_KEY`. O `config.js` está no `.gitignore`.

**Firmware:** abra `src/firmware/clip01/` no [Wokwi](https://wokwi.com) (ESP32), ou compile com:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32 src/firmware/clip01
```

---

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/fiap-tutoria/FIAP-PORTFOLIO-AI">TEMPLATE - FIAP PORTFÓLIO AI</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">FIAP</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
