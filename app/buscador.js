// Logica de busqueda pura (sin DOM): se usa en el navegador y en las pruebas de Node.

export function plano(s) {
  // Quita acentos conservando la longitud (posiciones alineadas con el texto original).
  return String(s).replace(/[\u00C0-\u024F]/g, (c) => c.normalize("NFD")[0]).toLowerCase();
}

export function tokens(q) {
  return [...new Set(plano(q).match(/[a-z0-9]{3,}/g) || [])];
}

const esAlnum = (ch) => /[a-z0-9]/.test(ch || "");
const conjunto = (s) => plano(s).match(/[a-z0-9]+/g)?.sort().join(" ") || "";

export function buscarFragmentos(texto, toks, frase, { ancho = 120, max = 2 } = {}) {
  const t = plano(texto);
  const base = t.length === texto.length ? texto : t;
  const ancla = [...toks].sort((a, b) => b.length - a.length)[0];
  const res = [];
  let i = 0;
  while (res.length < max && (i = t.indexOf(ancla, i)) !== -1) {
    if (esAlnum(t[i - 1]) || esAlnum(t[i + ancla.length])) { i += ancla.length; continue; }
    const ini = Math.max(0, i - ancho);
    const fin = Math.min(t.length, i + ancla.length + ancho);
    const ventana = t.slice(ini, fin);
    const todas = toks.every((k) => new RegExp(`(^|[^a-z0-9])${k}([^a-z0-9]|$)`).test(ventana));
    if (todas) {
      const compacta = " " + ventana.replace(/[^a-z0-9]+/g, " ") + " ";
      res.push({
        texto: base.slice(ini, fin).replace(/\s+/g, " ").trim(),
        exacta: compacta.includes(" " + frase + " "),
      });
      i = fin;
    } else {
      i += ancla.length;
    }
  }
  return res;
}

export class Buscador {
  constructor(base, fetchFn) {
    this.base = base.endsWith("/") ? base : base + "/";
    this.f = fetchFn || ((...a) => fetch(...a));
    this.cache = new Map();
  }

  async json(ruta, opcional = false) {
    if (this.cache.has(ruta)) return this.cache.get(ruta);
    const p = (async () => {
      const r = await this.f(this.base + ruta);
      if (!r.ok && opcional && r.status === 404) return null;
      if (!r.ok) throw new Error(`HTTP ${r.status} en ${ruta}`);
      return r.json();
    })();
    this.cache.set(ruta, p);
    try { return await p; } catch (e) { this.cache.delete(ruta); throw e; }
  }

  async posting(token) {
    const shard = await this.json(`idx/${token.slice(0, 2)}.json`, true);
    const deltas = shard && shard[token];
    if (!deltas) return [];
    let acc = 0;
    return deltas.map((d) => (acc += d));
  }

  async buscar(query) {
    const toks = tokens(query);
    if (!toks.length) return { estado: "vacio", toks, ids: [] };
    const frase = plano(query).replace(/[^a-z0-9]+/g, " ").trim();
    const comunes = new Set((await this.json("comunes.json", true)) || []);
    const usables = toks.filter((t) => !comunes.has(t));
    if (!usables.length) return { estado: "comun", toks, ids: [] };
    const listas = await Promise.all(usables.map((t) => this.posting(t)));
    listas.sort((a, b) => a.length - b.length);
    let ids = listas[0];
    for (const l of listas.slice(1)) { const s = new Set(l); ids = ids.filter((x) => s.has(x)); }
    return { estado: "ok", toks, frase, ids };
  }

  async coincidencias({ toks, frase, ids }, offset = 0, limite = 15) {
    const manifest = await this.json("manifest.json");
    const lote = ids.slice(offset, offset + limite);
    const packs = [...new Set(lote.map((i) => Math.floor(i / manifest.tam_pack)))];
    const datos = (await Promise.all(packs.map((p) => this.json(`t/${p}.json`)))).flat();
    const porId = new Map(datos.map((d) => [d.i, d]));
    const resultados = [];
    for (const id of lote) {
      const d = porId.get(id);
      if (!d) continue;
      const fragmentos = [];
      d.p.forEach((txt, k) => {
        if (txt === "[pagina retirada]") return;
        for (const f of buscarFragmentos(txt, toks, frase, { max: 1 })) fragmentos.push({ pagina: d.l[k], ...f });
      });
      if (fragmentos.length) {
        resultados.push({ id, titulo: d.t, tipo: d.y, resumen: d.s, url: d.u,
          fragmentos: fragmentos.slice(0, 3), exacta: fragmentos.some((f) => f.exacta) });
      }
    }
    resultados.sort((a, b) => Number(b.exacta) - Number(a.exacta));
    return { resultados, siguiente: offset + limite < ids.length ? offset + limite : null, total: ids.length };
  }

  async persona(query) {
    const idx = await this.json("personas/index.json", true);
    if (!idx) return null;
    const q = conjunto(query);
    const hit = idx.find((p) => p.claves.some((c) => conjunto(c) === q));
    return hit ? this.json(`personas/${hit.slug}.json`) : null;
  }
}
