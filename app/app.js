import { Buscador, plano } from "./buscador.js";

const cfg = window.ARCHIVOS_CONFIG || {};
const bus = new Buscador(cfg.baseDatos || "./data/");
const $ = (id) => document.getElementById(id);
const HOSTS = ["github.com", "justice.gov", "oversight.house.gov", "democrats-oversight.house.gov",
  "vault.fbi.gov", "courtlistener.com", "uscourts.gov", "govinfo.gov"];

function el(tag, clase, ...hijos) {
  const e = document.createElement(tag);
  if (clase) e.className = clase;
  for (const h of hijos) if (h !== null && h !== undefined) e.append(h);
  return e;
}

function enlaceSeguro(url, texto) {
  try {
    const u = new URL(url);
    if (u.protocol !== "https:" || !HOSTS.some((h) => u.hostname === h || u.hostname.endsWith("." + h))) return null;
    const a = el("a", "", texto);
    a.href = u.href; a.target = "_blank"; a.rel = "noopener noreferrer";
    return a;
  } catch { return null; }
}

function resaltado(texto, toks) {
  const frag = document.createDocumentFragment();
  const t = plano(texto);
  if (t.length !== texto.length || !toks.length) { frag.append(texto); return frag; }
  const re = new RegExp(`(^|[^a-z0-9])(${toks.join("|")})(?=[^a-z0-9]|$)`, "g");
  let ult = 0, m;
  while ((m = re.exec(t))) {
    const ini = m.index + m[1].length, fin = ini + m[2].length;
    frag.append(texto.slice(ult, ini), el("mark", "", texto.slice(ini, fin)));
    ult = fin;
  }
  frag.append(texto.slice(ult));
  return frag;
}

function enlaceReporte(titulo) {
  if (!cfg.repoWiki) return null;
  const a = el("a", "reporte", "Reportar / solicitar retiro");
  a.href = `https://github.com/${cfg.repoWiki}/issues/new?template=solicitud-retiro.md&title=${encodeURIComponent("Retiro: " + titulo)}`;
  a.target = "_blank"; a.rel = "noopener noreferrer";
  return a;
}

function tarjetaPersona(p) {
  const s = el("div", "tarjeta wiki");
  s.append(el("h2", "", p.nombre), el("p", "etiqueta", "Anotación de la comunidad · revisada por pares"));
  for (const m of p.menciones) {
    const caja = el("article", "mencion");
    const chips = el("p", "chips", el("span", "chip", m.categoria.replaceAll("_", " ")),
      el("span", m.verificacion === "documentada" ? "chip ok" : "chip alerta", m.verificacion.replaceAll("_", " ")));
    if (m.posible_homonimo) chips.append(el("span", "chip alerta", "posible homónimo"));
    caja.append(chips, el("blockquote", "", m.cita), el("p", "", m.contexto),
      el("p", "meta", `Según: ${m.atribucion} · ${m.documento.id_documento}, p. ${m.documento.pagina}`));
    const link = enlaceSeguro(m.documento.url, "Ver documento oficial");
    if (link) caja.append(link);
    s.append(caja);
  }
  return s;
}

function tarjetaDoc(r, toks) {
  const c = el("article", "tarjeta");
  c.append(el("h3", "", r.titulo));
  const meta = [r.tipo, r.exacta ? "coincidencia exacta" : "palabras cercanas"].filter(Boolean).join(" · ");
  c.append(el("p", "meta", meta));
  if (r.resumen) c.append(el("p", "resumen", r.resumen));
  for (const f of r.fragmentos) {
    const q = el("blockquote", "");
    q.append(el("span", "pag", `p. ${f.pagina}: `), "…", resaltado(f.texto, toks), "…");
    c.append(q);
  }
  const fila = el("p", "acciones");
  const l = enlaceSeguro(r.url, "Ver en GitHub");
  if (l) fila.append(l);
  const rep = enlaceReporte(r.titulo);
  if (rep) fila.append(rep);
  c.append(fila);
  return c;
}

let actual = null, offset = 0;

async function pintarLote() {
  const { resultados, siguiente, total } = await bus.coincidencias(actual, offset);
  for (const r of resultados) $("lista").append(tarjetaDoc(r, actual.toks));
  $("mas").hidden = siguiente === null;
  offset = siguiente ?? offset;
  if (!$("lista").children.length) {
    $("estado").textContent = total
      ? "Hay documentos que contienen esas palabras, pero separadas. Prueba con otra forma del nombre."
      : "";
  }
}

async function buscar(q) {
  $("estado").textContent = "Buscando…";
  for (const id of ["wiki", "auto"]) $(id).hidden = true;
  $("lista").replaceChildren(); $("wiki").replaceChildren(); $("mas").hidden = true;
  try {
    const [persona, b] = await Promise.all([bus.persona(q), bus.buscar(q)]);
    if (persona) { $("wiki").append(tarjetaPersona(persona)); $("wiki").hidden = false; }
    if (b.estado === "comun") { $("estado").textContent = "Ese término es demasiado común en los documentos. Añade nombre y apellido."; return; }
    if (b.estado === "vacio") { $("estado").textContent = "Escribe al menos 3 letras."; return; }
    if (!b.ids.length) {
      $("estado").textContent = "Sin coincidencias en el índice. Esto no prueba que la persona no aparezca: el OCR puede deformar nombres y el índice no incluye todos los documentos.";
      return;
    }
    $("estado").textContent = `${b.ids.length} documento(s) contienen esas palabras. El texto es OCR automático y puede tener errores.`;
    actual = b; offset = 0; $("auto").hidden = false;
    await pintarLote();
  } catch {
    $("estado").textContent = "No se pudo cargar el índice. Revisa tu conexión a internet.";
  }
}

$("form").addEventListener("submit", (e) => { e.preventDefault(); buscar($("q").value.trim()); });
$("mas").addEventListener("click", () => pintarLote().catch(() => { $("estado").textContent = "Error al cargar más resultados."; }));

bus.json("manifest.json").then((m) => {
  const f = new Date(m.generado).toLocaleDateString("es");
  $("pie").textContent = `Índice del ${f} · ${m.documentos.toLocaleString("es")} documentos · Fuente: repositorios comunitarios de GitHub. No es asesoría legal.`;
}).catch(() => { $("pie").textContent = "Índice no disponible por ahora."; });

if ("serviceWorker" in navigator && !window.Capacitor) navigator.serviceWorker.register("sw.js").catch(() => {});
