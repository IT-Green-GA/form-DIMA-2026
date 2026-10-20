import { createClient } from "@supabase/supabase-js";
import "./style.css";

// Inicializar cliente Supabase si existen credenciales válidas
const supabaseUrl = import.meta.env.SUPABASE_URL;
const supabaseKey = import.meta.env.SUPABASE_PUBLISHABLE_KEY;

let supabase = null;
let modoConexion = "local"; // 'supabase' | 'local'

if (supabaseUrl && supabaseKey && supabaseUrl.startsWith("http")) {
  try {
    supabase = createClient(supabaseUrl, supabaseKey);
    modoConexion = "supabase";
  } catch (e) {
    console.warn("No se pudo inicializar Supabase, usando almacenamiento local:", e);
    modoConexion = "local";
  }
}

// Elementos de la UI
const formulario = document.querySelector("#registro");
const botonGuardar = document.querySelector("#btn-guardar");
const estado = document.querySelector("#estado");
const filas = document.querySelector("#registros tbody");
const badgeConexion = document.querySelector("#badge-conexion");
const textoConexion = document.querySelector("#texto-conexion");

// Controles de métricas
const metricTotal = document.querySelector("#total-registros");
const metricCultivo = document.querySelector("#cultivo-top");
const metricRiego = document.querySelector("#ultimo-riego");
const metricParcela = document.querySelector("#parcela-activa");

// Controles de filtrado y exportación
const inputBusqueda = document.querySelector("#filtro-busqueda");
const filtroCultivo = document.querySelector("#filtro-cultivo");
const filtroActividad = document.querySelector("#filtro-actividad");
const btnExportarCsv = document.querySelector("#btn-exportar-csv");
const contadorMostrados = document.querySelector("#contador-mostrados");

// Estado local de registros
let todosLosRegistros = [];

// Formateador de fechas: 2026-10-19 → 19/10/2026
const formatoFecha = (fecha) => {
  if (!fecha) return "";
  return fecha.split("-").reverse().join("/");
};

// Generador de clase badge para cultivo
function obtenerClaseCultivo(cultivo = "") {
  const c = cultivo.toLowerCase();
  if (c.includes("maíz") || c.includes("maiz")) return "badge-cultivo-maiz";
  if (c.includes("frijol")) return "badge-cultivo-frijol";
  if (c.includes("haba")) return "badge-cultivo-haba";
  if (c.includes("avena")) return "badge-cultivo-avena";
  if (c.includes("hortaliza")) return "badge-cultivo-hortalizas";
  return "badge-cultivo-otro";
}

// Generador de clase badge para actividad
function obtenerClaseActividad(actividad = "") {
  const a = actividad.toLowerCase();
  if (a.includes("observación") || a.includes("observacion")) return "badge-actividad-observacion";
  if (a.includes("riego")) return "badge-actividad-riego";
  if (a.includes("fertiliz")) return "badge-actividad-fertilizacion";
  if (a.includes("muestreo")) return "badge-actividad-muestreo";
  if (a.includes("cosecha")) return "badge-actividad-cosecha";
  return "badge-actividad-otro";
}

// Actualizar el estado visual de conexión
function actualizarBadgeConexion(estadoConectado, mensaje) {
  if (estadoConectado) {
    badgeConexion.className = "status-badge status-online";
    textoConexion.textContent = mensaje || "Conectado a Supabase";
  } else {
    badgeConexion.className = "status-badge status-local";
    textoConexion.textContent = mensaje || "Modo Local (Offline)";
  }
}

// Actualizar tarjetas de métricas (Función 1)
function actualizarMetricas(registros) {
  metricTotal.textContent = registros.length;

  if (registros.length === 0) {
    metricCultivo.textContent = "-";
    metricRiego.textContent = "Sin registro";
    metricParcela.textContent = "-";
    return;
  }

  // Cultivo más frecuente
  const conteoCultivos = {};
  for (const r of registros) {
    if (r.cultivo) conteoCultivos[r.cultivo] = (conteoCultivos[r.cultivo] || 0) + 1;
  }
  const topCultivo = Object.entries(conteoCultivos).sort((a, b) => b[1] - a[1])[0];
  metricCultivo.textContent = topCultivo ? `${topCultivo[0]} (${topCultivo[1]})` : "-";

  // Último riego
  const riegos = registros.filter((r) => r.actividad && r.actividad.toLowerCase().includes("riego"));
  if (riegos.length > 0) {
    const ultimo = riegos[0]; // Ya vienen ordenados desc por fecha
    metricRiego.textContent = formatoFecha(ultimo.fecha);
  } else {
    metricRiego.textContent = "Ninguno aún";
  }

  // Parcela más activa
  const conteoParcelas = {};
  for (const r of registros) {
    if (r.parcela) conteoParcelas[r.parcela] = (conteoParcelas[r.parcela] || 0) + 1;
  }
  const topParcela = Object.entries(conteoParcelas).sort((a, b) => b[1] - a[1])[0];
  metricParcela.textContent = topParcela ? topParcela[0] : "-";
}

// Renderizar tabla con registros filtrados
function renderizarTabla(registros) {
  filas.replaceChildren();

  if (registros.length === 0) {
    const filaVacia = filas.insertRow();
    const celda = filaVacia.insertCell();
    celda.colSpan = 5;
    celda.className = "celda-vacia";
    celda.textContent = todosLosRegistros.length === 0
      ? "Todavía no hay registros. Completa el formulario para agregar el primero."
      : "No se encontraron registros con los filtros seleccionados.";
    contadorMostrados.textContent = `Mostrando 0 de ${todosLosRegistros.length} registros`;
    return;
  }

  contadorMostrados.textContent = `Mostrando ${registros.length} de ${todosLosRegistros.length} registros`;

  for (const r of registros) {
    const fila = filas.insertRow();

    // Fecha
    const cFecha = fila.insertCell();
    cFecha.className = "celda-fecha";
    cFecha.textContent = formatoFecha(r.fecha);

    // Parcela
    const cParcela = fila.insertCell();
    cParcela.className = "celda-parcela";
    cParcela.textContent = r.parcela || "-";

    // Cultivo (badge)
    const cCultivo = fila.insertCell();
    const badgeCult = document.createElement("span");
    badgeCult.className = `badge ${obtenerClaseCultivo(r.cultivo)}`;
    badgeCult.textContent = r.cultivo || "-";
    cCultivo.appendChild(badgeCult);

    // Actividad (badge)
    const cActividad = fila.insertCell();
    const badgeAct = document.createElement("span");
    badgeAct.className = `badge ${obtenerClaseActividad(r.actividad)}`;
    badgeAct.textContent = r.actividad || "-";
    cActividad.appendChild(badgeAct);

    // Observaciones
    const cObs = fila.insertCell();
    cObs.className = "celda-observaciones";
    cObs.textContent = r.observaciones ? r.observaciones : "—";
  }
}

// Aplicar filtros en tiempo real (Función 2)
function filtrarRegistros() {
  const query = (inputBusqueda.value || "").toLowerCase().trim();
  const selCultivo = filtroCultivo.value;
  const selActividad = filtroActividad.value;

  const filtrados = todosLosRegistros.filter((r) => {
    // Filtro cultivo
    if (selCultivo !== "todos" && r.cultivo !== selCultivo) return false;

    // Filtro actividad
    if (selActividad !== "todas" && r.actividad !== selActividad) return false;

    // Búsqueda en texto
    if (query) {
      const matchParcela = (r.parcela || "").toLowerCase().includes(query);
      const matchObs = (r.observaciones || "").toLowerCase().includes(query);
      const matchCultivo = (r.cultivo || "").toLowerCase().includes(query);
      if (!matchParcela && !matchObs && !matchCultivo) return false;
    }

    return true;
  });

  renderizarTabla(filtrados);
}

// Exportar a CSV (Función 3)
function exportarACSV() {
  if (todosLosRegistros.length === 0) {
    alert("No hay registros disponibles para exportar.");
    return;
  }

  // Encabezados
  const encabezados = ["ID", "Fecha", "Parcela", "Cultivo", "Actividad", "Observaciones"];
  
  // Filas en formato CSV
  const lineas = [
    encabezados.join(","),
    ...todosLosRegistros.map((r, i) => {
      const fila = [
        r.id ?? (i + 1),
        `"${r.fecha ?? ""}"`,
        `"${(r.parcela ?? "").replace(/"/g, '""')}"`,
        `"${(r.cultivo ?? "").replace(/"/g, '""')}"`,
        `"${(r.actividad ?? "").replace(/"/g, '""')}"`,
        `"${(r.observaciones ?? "").replace(/"/g, '""')}"`,
      ];
      return fila.join(",");
    }),
  ];

  // \uFEFF añade BOM para soporte nativo de caracteres con tilde y eñes en Microsoft Excel
  const blob = new Blob(["\uFEFF" + lineas.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  const fechaHoy = new Date().toISOString().split("T")[0];
  enlace.href = url;
  enlace.download = `bitacora_parcela_${fechaHoy}.csv`;
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
  URL.revokeObjectURL(url);
}

// Almacenamiento local auxiliar (Fallback)
const STORAGE_KEY = "bitacora_parcela_datos";
function obtenerLocales() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
function guardarLocales(datos) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(datos));
  } catch (e) {
    console.error("Error al guardar en localStorage", e);
  }
}

// Consultar registros
async function consultar() {
  if (supabase) {
    try {
      const { data, error } = await supabase
        .from("registros")
        .select("*")
        .order("fecha", { ascending: false });

      if (error) {
        console.warn("Error consultando Supabase, cargando locales:", error.message);
        actualizarBadgeConexion(false, "Modo Local (Supabase sin tabla)");
        todosLosRegistros = obtenerLocales();
      } else {
        actualizarBadgeConexion(true, "Conectado a Supabase");
        todosLosRegistros = data || [];
      }
    } catch (err) {
      console.warn("Excepción al consultar Supabase:", err);
      actualizarBadgeConexion(false, "Modo Local");
      todosLosRegistros = obtenerLocales();
    }
  } else {
    actualizarBadgeConexion(false, "Modo Local (Configura .env)");
    todosLosRegistros = obtenerLocales();
  }

  actualizarMetricas(todosLosRegistros);
  filtrarRegistros();
}

// Guardar nuevo registro
async function guardar(evento) {
  evento.preventDefault();
  const formData = new FormData(formulario);
  const nuevoRegistro = {
    fecha: formData.get("fecha"),
    parcela: formData.get("parcela"),
    cultivo: formData.get("cultivo"),
    actividad: formData.get("actividad"),
    observaciones: formData.get("observaciones") || "",
  };

  botonGuardar.disabled = true;
  estado.className = "estado";
  estado.textContent = "Guardando labor...";

  let guardadoEnSupabase = false;

  if (supabase) {
    try {
      const { error } = await supabase.from("registros").insert(nuevoRegistro);
      if (!error) {
        guardadoEnSupabase = true;
      } else {
        console.warn("No se pudo insertar en Supabase:", error.message);
      }
    } catch (err) {
      console.warn("Excepción al insertar en Supabase:", err);
    }
  }

  // Guardar en almacenamiento local como respaldo o modo offline
  if (!guardadoEnSupabase) {
    const locales = obtenerLocales();
    locales.unshift({ ...nuevoRegistro, id: Date.now() });
    guardarLocales(locales);
  }

  botonGuardar.disabled = false;
  estado.className = "estado exito";
  estado.textContent = guardadoEnSupabase
    ? "✅ Registro guardado exitosamente en Supabase."
    : "✅ Registro guardado en modo local.";

  formulario.observaciones.value = "";

  setTimeout(() => {
    estado.textContent = "";
    estado.className = "estado";
  }, 4000);

  consultar();
}

// Event Listeners
formulario.addEventListener("submit", guardar);
inputBusqueda.addEventListener("input", filtrarRegistros);
filtroCultivo.addEventListener("change", filtrarRegistros);
filtroActividad.addEventListener("change", filtrarRegistros);
btnExportarCsv.addEventListener("click", exportarACSV);

// Fecha de hoy por defecto
formulario.fecha.value = new Date().toLocaleDateString("en-CA");

// Carga inicial
consultar();
