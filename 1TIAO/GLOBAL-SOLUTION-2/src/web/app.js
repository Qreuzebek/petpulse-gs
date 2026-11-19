/* PetPulse (WARNED) — app web da POC.
 * Motor 1: Google Maps JS (vetorial, mapId) + deck.gl GoogleMapsOverlay (interleaved = WebGLOverlayView).
 * Motor 2 (sem chave): deck.gl standalone com tiles CARTO — mesmas camadas, mesma lógica.
 * TODOS os cães desta tela são SIMULADOS (Regra 8 da GS). */
(() => {
  const P = window.PetPulse;
  const CFG = window.PETPULSE_CONFIG || {};
  const $ = (id) => document.getElementById(id);
  const TTL_TICKS = 15 * 60; // 15 min em ticks de 1 s (a simulação acelera o tempo ×20)
  const EPS_M = 45;

  let ZONAS = [], SNAPS = [];
  let dogs = [], nextId = 9000, paused = false, kMin = 3, ver = 'B';
  let mode = 'live', replayIdx = 48, show3d = true, showZ = true;
  let selected = null; // {zona, lat, lng}
  let lastClusters = [], lastOcultos = 0, lastTick = Date.now();
  let engine = null; // {kind, setLayers, flyTo, setTilt, setStyle, styles}
  const elevCache = new Map(); // h3 -> {elev, fonte}

  // ---------- cotas ----------
  function cotaInterp(lat, lng) {
    let num = 0, den = 0;
    for (const z of ZONAS) { const d = Math.hypot(lat - z.lat, lng - z.lng) + 1e-6, w = 1 / d ** 2; num += w * z.cota_m; den += w; }
    return Math.round((num / den) * 10) / 10;
  }
  function cota(lat, lng) {
    const cell = h3.latLngToCell(lat, lng, 10);
    if (elevCache.has(cell)) return elevCache.get(cell).elev;
    const v = cotaInterp(lat, lng);
    elevCache.set(cell, { elev: v, fonte: 'referência' });
    if (engine && engine.elevation) engine.elevation(cell, lat, lng);
    return v;
  }

  // ---------- simulação ----------
  const rnd = (a, b) => a + Math.random() * (b - a);
  const gauss = (s) => (Math.random() + Math.random() + Math.random() - 1.5) * s * 1.4;
  function spawn(zIdx, n) {
    const z = ZONAS[zIdx];
    for (let i = 0; i < n; i++) {
      const porte = ['PEQUENO', 'MÉDIO', 'MÉDIO', 'GRANDE', 'GRANDE', 'GIGANTE'][Math.floor(Math.random() * 6)];
      const peso = { PEQUENO: 7, 'MÉDIO': 16, GRANDE: 30, GIGANTE: 50 }[porte];
      dogs.push({ id: nextId++, zona: z.nome, lat: z.lat + gauss(0.0003), lng: z.lng + gauss(0.0003),
        alturaRef: P.PORTES[porte] + gauss(2), base: peso * rnd(0.08, 0.3), kgf: 1, pk: 1, z: P.PORTES[porte], jump: 0, extra: 0,
        ttl: Math.floor(rnd(0.4, 1) * TTL_TICKS) });
    }
  }
  const thor = { id: 8695, zona: 'Parque Ibirapuera · Portão 7', lat: -23.5843, lng: -46.6492, alturaRef: 61,
    base: 3.4, kgf: 3.4, pk: 8.6, z: 61, jump: 0, extra: 0, ttl: Infinity, own: true, hist: [] };

  function stepDogs() {
    for (const d of [...dogs, thor]) {
      d.lat += gauss(0.00003); d.lng += gauss(0.00003);
      d.extra *= 0.35; d.jump *= 0.4;
      d.kgf = Math.max(0.2, d.base + gauss(d.base * 0.3) + d.extra + (Math.random() < 0.02 ? rnd(6, 10) : 0));
      d.pk = Math.max(d.pk * 0.995, d.kgf);
      d.z = d.alturaRef + gauss(2.5) + d.jump;
      d.ttl -= 20;
    }
    dogs = dogs.filter((d) => d.ttl > 0);
    // fluxo contínuo: repõe cães de acordo com a popularidade de cada zona
    ZONAS.forEach((z, i) => { if (Math.random() < [0.9, 0.55, 0.6, 0.45, 0.4, 0.3][i]) spawn(i, 1); });
  }

  function computeLive() {
    const all = [...dogs, thor];
    const labels = P.dbscan(all, EPS_M, kMin);
    const r = P.agrega(all, labels, kMin, h3, cota);
    return r;
  }

  // ---------- camadas ----------
  const ramp = (v) => {
    if (ver === 'A') { const t = v / 100; return [255, Math.round(200 - 110 * t), Math.round(150 - 119 * t), 235]; }
    const g = Math.round(225 - 200 * (v / 100)); return [g, g + 1, g + 3, 235];
  };
  function layers() {
    const hexData = [];
    for (const c of lastClusters) for (const cell of c.cells || [c.h3]) hexData.push({ hex: cell, c });
    const sel = selected && lastClusters.find((c) => c === selected.ref);
    const L = [
      new deck.H3HexagonLayer({
        id: 'hex', data: hexData, getHexagon: (d) => d.hex, extruded: show3d, elevationScale: 1,
        getElevation: (d) => (d.hex === d.c.h3 ? 2 + d.c.dbm * 0.5 : 1 + d.c.dbm * 0.25),
        getFillColor: (d) => ramp(d.c.dbm), getLineColor: [244, 244, 242], lineWidthMinPixels: 1, stroked: true,
        pickable: true, onClick: ({ object }) => object && select(object.c),
        updateTriggers: { getFillColor: [ver], getElevation: [show3d] },
        transitions: { getElevation: 600 },
      }),
    ];
    if (showZ) {
      L.push(new deck.ColumnLayer({
        id: 'z', data: lastClusters, diskResolution: 24, radius: 7, extruded: true,
        getPosition: (c) => [c.lng, c.lat, 0], getElevation: (c) => (show3d ? 2 + c.dbm * 0.5 : 0) + c.z_medio_cm * 0.5,
        getFillColor: ver === 'A' ? [14, 15, 16, 255] : [255, 90, 31, 255], pickable: true,
        onClick: ({ object }) => object && select(object), updateTriggers: { getElevation: [show3d], getFillColor: [ver] },
      }));
    }
    L.push(new deck.TextLayer({
      id: 'lbl', data: lastClusters, getPosition: (c) => [c.lng, c.lat, (show3d ? 2 + c.dbm * 0.5 : 0) + (showZ ? c.z_medio_cm * 0.5 : 0) + 6],
      getText: (c) => `${c.n_caes} CÃES · ${c.tracao_media_kgf}kgf · Z: ${c.z_medio_cm}cm · ${c.cota_m}m`,
      characterSet: 'auto', getSize: 12, fontFamily: 'JetBrains Mono, monospace', getColor: [244, 244, 242], background: true,
      getBackgroundColor: [14, 15, 16, 230], backgroundPadding: [6, 3], billboard: true,
    }));
    if (mode === 'live') {
      L.push(new deck.ScatterplotLayer({
        id: 'thor', data: [thor], getPosition: (d) => [d.lng, d.lat, 2], getRadius: 6, radiusMinPixels: 6,
        getFillColor: [14, 15, 16], getLineColor: [244, 244, 242], stroked: true, lineWidthMinPixels: 2,
      }));
    }
    if (sel) {
      L.push(new deck.H3HexagonLayer({ id: 'sel', data: sel.cells || [sel.h3], getHexagon: (d) => d, extruded: false,
        filled: false, stroked: true, getLineColor: [255, 90, 31], lineWidthMinPixels: 3 }));
    }
    return L;
  }

  // ---------- painel ----------
  function select(c) { selected = { zona: c.zona, lat: c.lat, lng: c.lng, ref: c }; renderPanel(); render(); }
  function refreshSelection() {
    if (!selected) return;
    const cand = lastClusters.filter((c) => c.zona === selected.zona)
      .sort((a, b) => P.haversine(a, selected) - P.haversine(b, selected))[0];
    selected.ref = cand || null;
  }
  function renderPanel() {
    const c = selected && selected.ref;
    $('zone').hidden = !c; $('zoneEmpty').hidden = !!c;
    if (!c) return;
    $('zNome').textContent = c.zona;
    const el = elevCache.get(c.h3);
    $('zH3').textContent = `H3 RES-10: ${c.h3} · + ${c.h3_adj} adj · cota via ${el ? el.fonte : 'pipeline'}`;
    $('zPets').textContent = c.n_caes; $('zAdj').textContent = `+${c.h3_adj} adj`; $('zElev').textContent = `${c.cota_m} m`;
    $('zMark').style.left = `calc(${c.dbm}% - 2px)`;
    $('zTr').textContent = `${c.tracao_media_kgf} kgf`; $('zTrN').textContent = `${P.kgfToN(c.tracao_media_kgf)} N`;
    $('zPk').textContent = `${c.pico_kgf} kgf`; $('zPkN').textContent = `${P.kgfToN(c.pico_kgf)} N máx`;
    $('zDbm').textContent = c.dbm;
    const tot = c.n_caes || 1, fx = c.faixas;
    $('zFaixas').innerHTML = [['Guia Frouxa (<2.5 kgf)', fx.FROUXA], ['Tração (2.5–8 kgf)', fx.TRACAO], ['Tranco (>8 kgf)', fx.TRANCO]]
      .map(([l, v]) => `<div class="bar"><span>${l}</span><i style="width:${(100 * v) / tot}%"></i><span class="mono">${v}</span></div>`).join('');
    $('badgeTracao').hidden = c.tracao_media_kgf < 5;
    $('zZ').textContent = `${c.z_medio_cm} cm`; $('zAmp').textContent = `${c.z_min_cm}–${c.z_max_cm}`; $('zCota').textContent = `${c.cota_m} m`;
    const top = Object.entries(c.portes).sort((a, b) => b[1] - a[1])[0][0];
    $('zPortes').innerHTML = Object.entries(c.portes).map(([k, v]) =>
      `<div class="${k === top ? 'top' : ''}">${k}<br>~${P.PORTES[k]} cm<br>${v} · ${Math.round((100 * v) / tot)}%</div>`).join('');
    $('coords').textContent = `LAT/LNG ${c.lat.toFixed(5)}, ${c.lng.toFixed(5)} · COTA GOOGLE: ${c.cota_m} m · H3: ${c.h3}`;
  }
  function renderClip() {
    $('kgf').textContent = thor.kgf.toFixed(1); $('newton').textContent = `${P.kgfToN(thor.kgf)} N`;
    $('pk').textContent = thor.pk.toFixed(1);
    $('faixa').textContent = { FROUXA: 'GUIA FROUXA', TRACAO: 'TRAÇÃO', TRANCO: 'TRANCO' }[P.faixa(thor.kgf)];
    const g = cota(thor.lat, thor.lng), sensor = g + thor.z / 100;
    $('zform').textContent = `Z_cão = (${sensor.toFixed(2)} − ${g.toFixed(2)}) × 100 = ${P.zCaoCm(sensor, g)} cm`;
  }

  function render() {
    if (mode === 'replay') {
      const s = SNAPS[replayIdx];
      lastClusters = s.clusters.filter((c) => c.n_caes >= kMin); lastOcultos = s.ocultos;
      $('replayLbl').textContent = `18/11 ${s.t} · base Python`;
    }
    refreshSelection();
    engine && engine.setLayers(layers());
    $('stats').textContent = `${mode === 'live' ? dogs.length + 1 : '—'} ativos · ${lastClusters.length} zonas públicas · ${lastOcultos} ocultos (LGPD)`;
    renderPanel();
  }

  function tick() {
    if (!paused && mode === 'live') {
      stepDogs();
      const r = computeLive(); lastClusters = r.clusters; lastOcultos = r.ocultos;
      lastTick = Date.now();
      renderClip(); render();
    }
    const s = Math.max(1, Math.round((Date.now() - lastTick) / 1000));
    $('ago').textContent = $('ago2').textContent = `há ${s} s`;
  }

  // ---------- motores de mapa ----------
  const CENTER = { lat: -23.5862, lng: -46.6650 };
  function deckEngine() {
    const TILES = {
      'Silver (Esri Light Gray)': 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      'Night (Esri Dark Gray)': 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      'Padrão (OpenStreetMap)': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      'Satélite (Esri Imagery)': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    };
    let tileUrl = Object.values(TILES)[0], viewState = { longitude: CENTER.lng, latitude: CENTER.lat, zoom: 15.3, pitch: 45, bearing: -12 };
    const base = () => new deck.TileLayer({ id: 'base-' + tileUrl, data: tileUrl, minZoom: 0, maxZoom: 16, tileSize: 256,
      renderSubLayers: (p) => { const { west, south, east, north } = p.tile.bbox;
        return new deck.BitmapLayer(p, { data: null, image: p.data, bounds: [west, south, east, north] }); } });
    let extra = [];
    const d = new deck.Deck({ parent: $('map'), initialViewState: viewState, controller: true,
      onViewStateChange: ({ viewState: v }) => { viewState = v; d.setProps({ viewState }); },
      viewState, layers: [base()],
      getTooltip: ({ object }) => object && object.c ? `${object.c.zona}\nDBM ${object.c.dbm}` : null });
    return {
      kind: 'deck.gl WebGL · Esri/OSM (sem chave Google)', styles: Object.keys(TILES),
      setLayers: (l) => { extra = l; d.setProps({ layers: [base(), ...extra] }); },
      setStyle: (name) => { tileUrl = TILES[name]; d.setProps({ layers: [base(), ...extra] }); },
      setTilt: (on) => { viewState = { ...viewState, pitch: on ? 45 : 0, transitionDuration: 500 }; d.setProps({ viewState }); },
      flyTo: (lat, lng) => { viewState = { ...viewState, latitude: lat, longitude: lng, zoom: 16.4, transitionDuration: 900,
        transitionInterpolator: new deck.FlyToInterpolator() }; d.setProps({ viewState }); },
    };
  }

  function googleEngine(done) {
    window.__ppInitGoogle = () => {
      const g = google.maps;
      const STY = { 'Google Silver': 'roadmap', 'Google Padrão': 'roadmap', 'Google Night': 'roadmap', 'Satélite Híbrido': 'hybrid' };
      let map, overlay = new deck.GoogleMapsOverlay({ interleaved: true, layers: [] });
      const make = (scheme, typeId, keep) => {
        map = new g.Map($('map'), { center: keep ? keep.getCenter() : CENTER, zoom: keep ? keep.getZoom() : 16,
          tilt: 45, heading: -12, mapId: CFG.mapId || 'DEMO_MAP_ID', mapTypeId: typeId,
          colorScheme: scheme, disableDefaultUI: true, gestureHandling: 'greedy' });
        overlay.setMap(map);
        map.addListener('click', (e) => {
          const lat = e.latLng.lat(), lng = e.latLng.lng();
          $('coords').textContent = `LAT/LNG ${lat.toFixed(5)}, ${lng.toFixed(5)} · COTA GOOGLE: ${cota(lat, lng)} m · H3: ${h3.latLngToCell(lat, lng, 10)}`;
        });
      };
      make(g.ColorScheme ? g.ColorScheme.LIGHT : undefined, 'roadmap');
      const elev = new g.ElevationService();
      const pend = new Set();
      done({
        kind: 'Google Maps WebGLOverlayView · Elevation API', styles: Object.keys(STY),
        setLayers: (l) => overlay.setProps({ layers: l }),
        setStyle: (name) => {
          const dark = name === 'Google Night';
          make(g.ColorScheme ? (dark ? g.ColorScheme.DARK : g.ColorScheme.LIGHT) : undefined, STY[name], map);
        },
        setTilt: (on) => map.setTilt(on ? 45 : 0),
        flyTo: (lat, lng) => map.moveCamera({ center: { lat, lng }, zoom: 16.6, tilt: show3d ? 45 : 0 }),
        elevation: (cell, lat, lng) => {
          if (pend.has(cell)) return; pend.add(cell);
          const [clat, clng] = h3.cellToLatLng(cell);
          elev.getElevationForLocations({ locations: [{ lat: clat, lng: clng }] }).then((r) => {
            if (r.results && r.results[0]) elevCache.set(cell, { elev: Math.round(r.results[0].elevation * 10) / 10, fonte: 'Google Elevation API' });
          }).catch(() => {});
        },
      });
    };
    const s = document.createElement('script');
    s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(CFG.googleMapsApiKey)}&v=weekly&callback=__ppInitGoogle`;
    s.async = true; s.onerror = () => done(null);
    document.head.appendChild(s);
  }

  function useEngine(e) {
    engine = e;
    $('engine').textContent = e.kind;
    $('estilo').innerHTML = e.styles.map((s) => `<option>${s}</option>`).join('');
    render();
  }

  // ---------- controles ----------
  function wire() {
    $('b3d').onclick = (ev) => { show3d = !show3d; ev.target.classList.toggle('on', show3d); engine.setTilt(show3d); render(); };
    $('bz').onclick = (ev) => { showZ = !showZ; ev.target.classList.toggle('on', showZ); ev.target.textContent = `EIXO Z (CM): ${showZ ? 'ON' : 'OFF'}`; render(); };
    $('estilo').onchange = (ev) => { engine.setStyle(ev.target.value); render(); };
    document.querySelectorAll('[data-go]').forEach((b) => (b.onclick = () => {
      const z = ZONAS[+b.dataset.go]; engine.flyTo(z.lat, z.lng);
      const c = lastClusters.filter((x) => x.zona === z.nome).sort((a, b) => b.n_caes - a.n_caes)[0];
      if (c) select(c); else { selected = { zona: z.nome, lat: z.lat, lng: z.lng, ref: null }; renderPanel(); }
    }));
    const pux = () => { thor.extra = 15; thor.kgf += 15; thor.pk = Math.max(thor.pk, thor.kgf);
      dogs.filter((d) => selected && d.zona === selected.zona).forEach((d) => (d.extra = 15)); renderClip(); };
    $('bpux').onclick = pux; $('bPux2').onclick = pux;
    $('bsalto').onclick = () => { thor.jump = rnd(18, 32); renderClip(); };
    let led = false;
    $('bled').onclick = (ev) => { led = !led; ev.target.classList.toggle('on', led);
      document.querySelector('.clip').classList.toggle('led', led);
      $('bat').textContent = led ? '34µA · 76d' : '14µA · 184d'; };
    $('bVer').onclick = (ev) => { ver = ver === 'B' ? 'A' : 'B'; document.body.dataset.ver = ver;
      ev.target.textContent = ver === 'B' ? 'VER B · NEUTRA (MONO)' : 'VER A · SINAL BOLD'; render(); };
    $('bPause').onclick = (ev) => { paused = !paused; ev.target.textContent = paused ? 'RETOMAR' : 'PAUSAR'; ev.target.classList.toggle('on', paused); };
    $('b12').onclick = () => { const i = selected ? Math.max(0, ZONAS.findIndex((z) => z.nome === selected.zona)) : 0; spawn(i, 12); };
    $('bPico').onclick = () => ZONAS.forEach((_, i) => spawn(i, [30, 16, 18, 12, 10, 8][i]));
    $('nMin').oninput = (ev) => { kMin = +ev.target.value; $('nVal').textContent = kMin; if (mode === 'replay') render(); };
    $('mLive').onclick = () => { mode = 'live'; $('mLive').classList.add('on'); $('mReplay').classList.remove('on');
      $('replayT').hidden = $('replayLbl').hidden = true; };
    $('mReplay').onclick = () => { mode = 'replay'; $('mReplay').classList.add('on'); $('mLive').classList.remove('on');
      $('replayT').hidden = $('replayLbl').hidden = false; render(); };
    $('replayT').oninput = (ev) => { replayIdx = +ev.target.value; render(); };
  }

  async function boot() {
    const data = await fetch('data/snapshots.json').then((r) => r.json());
    ZONAS = data.zonas; SNAPS = data.snapshots;
    $('replayT').max = SNAPS.length - 1;
    ZONAS.forEach((_, i) => spawn(i, [14, 7, 8, 6, 5, 4][i]));
    wire();
    const fallback = () => useEngine(deckEngine());
    if (CFG.googleMapsApiKey) googleEngine((e) => (e ? useEngine(e) : fallback()));
    else fallback();
    tick(); setInterval(tick, 1000);
    window.__pp = { get clusters() { return lastClusters; }, get dogs() { return dogs; }, thor };
  }
  boot();
})();
