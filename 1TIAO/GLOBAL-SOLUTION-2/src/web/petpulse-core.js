/* PetPulse core — mesmas regras do pacote Python (src/petpulse), para a simulação ao vivo no navegador.
 * Funções puras; testadas em src/web/test-core.mjs (node). */
(function (root) {
  const KGF_TO_N = 9.80665, FROUXA = 2.5, TRANCO = 8, R = 6371000;
  const PORTES = { PEQUENO: 28, 'MÉDIO': 46, GRANDE: 62, GIGANTE: 78 };

  const kgfToN = (kgf) => Math.round(kgf * KGF_TO_N);
  const faixa = (kgf) => (kgf < FROUXA ? 'FROUXA' : kgf <= TRANCO ? 'TRACAO' : 'TRANCO');
  const zCaoCm = (elevSensor, googleElev) => Math.round((elevSensor - googleElev) * 1000) / 10;
  const porte = (z) => Object.keys(PORTES).reduce((a, b) => (Math.abs(PORTES[b] - z) < Math.abs(PORTES[a] - z) ? b : a));

  /** Índice DBM (Densidade·Biomecânica·Movimento) — log, 0–100. NÃO é dBm de RF. */
  function dbm(n, tracaoKgf, amplitudeCm, ref = 40 * 18 * 1.0) {
    if (n <= 0) return 0;
    const I = n * Math.max(tracaoKgf, 0) * Math.max(amplitudeCm, 0) / 100;
    return Math.round(Math.min(100, Math.max(0, 100 * Math.log10(1 + I) / Math.log10(1 + ref))));
  }

  function haversine(a, b) {
    const toR = Math.PI / 180, dLat = (b.lat - a.lat) * toR, dLng = (b.lng - a.lng) * toR;
    const s = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * toR) * Math.cos(b.lat * toR) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(s));
  }

  /** DBSCAN clássico (min_samples inclui o próprio ponto, como no scikit-learn). -1 = ruído. */
  function dbscan(pts, epsM, minPts) {
    const labels = new Array(pts.length).fill(undefined);
    const vizinhos = (i) => pts.reduce((acc, p, j) => (haversine(pts[i], p) <= epsM ? (acc.push(j), acc) : acc), []);
    let c = -1;
    for (let i = 0; i < pts.length; i++) {
      if (labels[i] !== undefined) continue;
      const n = vizinhos(i);
      if (n.length < minPts) { labels[i] = -1; continue; }
      labels[i] = ++c;
      const fila = n.filter((j) => j !== i);
      while (fila.length) {
        const j = fila.shift();
        if (labels[j] === -1) labels[j] = c;
        if (labels[j] !== undefined) continue;
        labels[j] = c;
        const nj = vizinhos(j);
        if (nj.length >= minPts) fila.push(...nj);
      }
    }
    return labels;
  }

  /** Agrega clusters e aplica k-anonymity: só sai o que tem >= kMin cães. Nunca expõe ids. */
  function agrega(caes, labels, kMin, h3lib, cotaFn) {
    const grupos = new Map();
    let ocultos = 0;
    labels.forEach((l, i) => { if (l < 0) { ocultos++; return; } if (!grupos.has(l)) grupos.set(l, []); grupos.get(l).push(caes[i]); });
    const out = [];
    for (const [cid, g] of grupos) {
      if (new Set(g.map((d) => d.id)).size < kMin) { ocultos += g.length; continue; }
      const lat = g.reduce((s, d) => s + d.lat, 0) / g.length, lng = g.reduce((s, d) => s + d.lng, 0) / g.length;
      const cell = h3lib ? h3lib.latLngToCell(lat, lng, 10) : null;
      const cells = h3lib ? [...new Set(g.map((d) => h3lib.latLngToCell(d.lat, d.lng, 10)))] : [];
      const tr = g.reduce((s, d) => s + d.kgf, 0) / g.length;
      const zs = g.map((d) => d.z), zmin = Math.min(...zs), zmax = Math.max(...zs);
      const fx = { FROUXA: 0, TRACAO: 0, TRANCO: 0 }; g.forEach((d) => fx[faixa(d.kgf)]++);
      const pt = { PEQUENO: 0, 'MÉDIO': 0, GRANDE: 0, GIGANTE: 0 }; g.forEach((d) => pt[porte(d.alturaRef)]++);
      const zonaCount = {}; g.forEach((d) => (zonaCount[d.zona] = (zonaCount[d.zona] || 0) + 1));
      out.push({
        cluster_id: cid, zona: Object.keys(zonaCount).sort((a, b) => zonaCount[b] - zonaCount[a])[0],
        lat, lng, h3: cell, h3_adj: cells.filter((c) => c !== cell).length, cells,
        n_caes: g.length, tracao_media_kgf: +tr.toFixed(1), pico_kgf: +Math.max(...g.map((d) => d.pk)).toFixed(1),
        z_medio_cm: Math.round(zs.reduce((s, z) => s + z, 0) / zs.length), z_min_cm: Math.round(zmin), z_max_cm: Math.round(zmax),
        cota_m: cotaFn ? cotaFn(lat, lng) : null, dbm: dbm(g.length, tr, zmax - zmin), faixas: fx, portes: pt,
      });
    }
    return { clusters: out, ocultos };
  }

  root.PetPulse = { kgfToN, faixa, zCaoCm, porte, dbm, haversine, dbscan, agrega, PORTES };
  if (typeof module !== 'undefined') module.exports = root.PetPulse;
})(typeof window !== 'undefined' ? window : globalThis);
