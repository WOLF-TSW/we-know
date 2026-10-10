// Prueba de extremo a extremo de la logica de busqueda con datos sinteticos.
// Uso: node tests/test_buscador.mjs <carpeta_data>
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import assert from "node:assert/strict";
import { Buscador } from "../app/buscador.js";

const dir = process.argv[2];
const fakeFetch = async (url) => {
  const ruta = join(dir, url.replace(/^https:\/\/fake\//, ""));
  try { const t = await readFile(ruta, "utf8"); return { ok: true, status: 200, json: async () => JSON.parse(t) }; }
  catch { return { ok: false, status: 404, json: async () => ({}) }; }
};
const b = new Buscador("https://fake/", fakeFetch);

// 1. Nombre presente: ambos documentos, con coincidencias exactas y cercanas
let r = await b.buscar("Persona Ejemplo");
assert.equal(r.estado, "ok"); assert.deepEqual(r.ids, [0, 1]);
let c = await b.coincidencias(r);
assert.equal(c.resultados.length, 2);
const docA = c.resultados.find((x) => x.titulo === "DOC-A");
assert.equal(docA.tipo, "correo"); assert.equal(docA.fragmentos.length, 2);
assert.ok(docA.fragmentos[0].exacta && !docA.fragmentos[1].exacta, "p1 exacta, p2 palabras cercanas");

// 2. Acentos y mayusculas
r = await b.buscar("REUNIÓN"); assert.deepEqual(r.ids, [0]);

// 3. Pagina retirada no es buscable ni aparece
r = await b.buscar("frase secreta 123"); assert.deepEqual(r.ids, []);

// 4. Nombre inexistente
r = await b.buscar("Fulano Inexistente"); assert.deepEqual(r.ids, []);

// 5. Entrada vacia / muy corta
r = await b.buscar("ab"); assert.equal(r.estado, "vacio");

// 6. Anotacion de la wiki (orden invertido del nombre tambien coincide)
let p = await b.persona("persona ejemplo"); assert.equal(p.nombre, "Persona Ejemplo");
p = await b.persona("Ejemplo, Persona"); assert.equal(p.nombre, "Persona Ejemplo");
assert.equal(await b.persona("Otra Cosa"), null);

console.log("Todas las pruebas de busqueda pasaron.");
