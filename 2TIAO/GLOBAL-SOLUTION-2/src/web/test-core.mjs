// Testes do núcleo JS (paridade com o Python).  Rodar: node src/web/test-core.mjs
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const P = createRequire(import.meta.url)('./petpulse-core.js');

assert.equal(P.kgfToN(3.4), 33);
assert.equal(P.kgfToN(13.6), 133);
assert.equal(P.kgfToN(18.3), 179);
assert.equal(P.faixa(2.4), 'FROUXA');
assert.equal(P.faixa(8), 'TRACAO');
assert.equal(P.faixa(8.1), 'TRANCO');
assert.equal(P.zCaoCm(752.71, 752.10), 61);
assert.equal(P.porte(61), 'GRANDE');
assert.equal(P.dbm(0, 5, 5), 0);
assert.equal(P.dbm(500, 50, 300), 100);
assert.ok(P.dbm(20, 10, 50) < 2 * P.dbm(10, 10, 50));
// mesmo valor que o Python: indice_dbm(13, 13.6, 70)
assert.equal(P.dbm(13, 13.6, 70), 73);

const caes = [[-23.58438, -46.64939], [-23.5844, -46.64945], [-23.58435, -46.6493], [-23.6, -46.7]]
  .map(([lat, lng], i) => ({ id: i, lat, lng, kgf: 4, pk: 9, z: 50, alturaRef: 46, zona: 'Z' }));
const lab = P.dbscan(caes, 45, 3);
assert.ok(lab[0] === lab[1] && lab[1] === lab[2] && lab[0] >= 0);
assert.equal(lab[3], -1);
const { clusters, ocultos } = P.agrega(caes, lab, 3, null, () => 750);
assert.equal(clusters.length, 1);
assert.equal(ocultos, 1);
assert.ok(!('id' in clusters[0]));
const k4 = P.agrega(caes, lab, 4, null, () => 750);
assert.equal(k4.clusters.length, 0);
console.log('core JS: todos os testes passaram');
