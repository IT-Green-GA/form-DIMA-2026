import { createClient } from "@supabase/supabase-js";
import "./style.css";

// La URL y la llave se leen de .env al iniciar o construir la aplicación.
const SUPABASE_URL = import.meta.env.SUPABASE_URL;
const SUPABASE_KEY = import.meta.env.SUPABASE_PUBLISHABLE_KEY;
const supabaseConfigurado = Boolean(SUPABASE_URL && SUPABASE_KEY);
const supabase = supabaseConfigurado
  ? createClient(SUPABASE_URL, SUPABASE_KEY)
  : null;

const formulario = document.querySelector("#registro");
const boton = formulario.querySelector('button[type="submit"]');
const estado = document.querySelector("#estado");
const filas = document.querySelector("#registros tbody");

// 2026-10-19 → 19/10/2026
const formatoFecha = (fecha) => fecha.split("-").reverse().join("/");

// Devuelve la fecha de hoy en formato YYYY-MM-DD según la zona horaria local.
const hoyISO = () => {
  const d = new Date();
  const anio = d.getFullYear();
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${anio}-${mes}-${dia}`;
};

// Selector de fecha: "hoy" usa la fecha de la computadora; "otra" deja elegir al usuario.
const opcionesFecha = document.querySelectorAll(".opcion-fecha");
const inputFechaTipo = document.querySelector('input[name="fecha-tipo"]');
const inputFecha = document.querySelector("#fecha");

function actualizarFecha() {
  if (!inputFechaTipo || !inputFecha) return;
  const tipoSeleccionado = inputFechaTipo.value || "hoy";
  opcionesFecha.forEach((op) => {
    const esActivo = op.dataset.valor === tipoSeleccionado;
    op.classList.toggle("activo", esActivo);
    op.setAttribute("aria-pressed", String(esActivo));
  });
  if (tipoSeleccionado === "hoy") {
    inputFecha.value = hoyISO();
    inputFecha.readOnly = true;
  } else {
    inputFecha.readOnly = false;
    if (!inputFecha.value) inputFecha.value = hoyISO();
  }
}

opcionesFecha.forEach((op) => {
  op.addEventListener("click", (evento) => {
    evento.preventDefault();
    inputFechaTipo.value = op.dataset.valor;
    actualizarFecha();
  });
});

// Almacén temporal cuando Supabase no está configurado (modo demo).
const CLAVE_LOCAL = "bitacora_registros";
const registrosLocales = JSON.parse(localStorage.getItem(CLAVE_LOCAL) || "[]");

function mostrar(registros) {
  filas.replaceChildren();
  if (registros.length === 0) {
    const celda = filas.insertRow().insertCell();
    celda.colSpan = 5;
    celda.textContent = "Todavía no hay registros.";
    return;
  }
  for (const r of registros) {
    const fila = filas.insertRow();

    const celdaFecha = fila.insertCell();
    celdaFecha.textContent = formatoFecha(r.fecha);

    const celdaParcela = fila.insertCell();
    celdaParcela.textContent = r.parcela;

    const celdaCultivo = fila.insertCell();
    const chipCultivo = document.createElement("span");
    chipCultivo.className = "chip chip-cultivo";
    chipCultivo.textContent = r.cultivo;
    celdaCultivo.appendChild(chipCultivo);

    const celdaActividad = fila.insertCell();
    const chipActividad = document.createElement("span");
    chipActividad.className = "chip chip-actividad";
    chipActividad.textContent = r.actividad;
    celdaActividad.appendChild(chipActividad);

    const celdaObs = fila.insertCell();
    celdaObs.textContent = r.observaciones ?? "";
  }
}

async function consultar() {
  if (!supabaseConfigurado) {
    mostrar(registrosLocales);
    return;
  }
  const { data, error } = await supabase
    .from("registros")
    .select("*")
    .order("fecha", { ascending: false });
  if (error) {
    console.error(error);
    estado.textContent = "No se pudieron cargar los registros.";
    return;
  }
  mostrar(data);
}

// Guardar un registro
async function guardar(evento) {
  evento.preventDefault();

  // Asegurarse de que la fecha siempre tenga el valor correcto.
  if (inputFechaTipo.value === "hoy") inputFecha.value = hoyISO();

  const { fecha, parcela, cultivo, actividad, observaciones } = Object.fromEntries(
    new FormData(formulario),
  );

  if (!fecha || !parcela || !cultivo || !actividad) {
    estado.textContent = "Faltan datos obligatorios.";
    return;
  }

  boton.disabled = true;

  if (!supabaseConfigurado) {
    registrosLocales.unshift({ fecha, parcela, cultivo, actividad, observaciones });
    localStorage.setItem(CLAVE_LOCAL, JSON.stringify(registrosLocales));
    estado.textContent = "Registro guardado (modo local: configura Supabase para persistencia).";
    formulario.observaciones.value = "";
    boton.disabled = false;
    mostrar(registrosLocales);
    return;
  }

  const { error } = await supabase
    .from("registros")
    .insert({ fecha, parcela, cultivo, actividad, observaciones });
  boton.disabled = false;

  if (error) {
    console.error(error);
    estado.textContent = "No se pudo guardar el registro.";
    return;
  }
  estado.textContent = "Registro guardado.";
  formulario.observaciones.value = "";
  consultar();
}

// Inicializar el selector de fecha (por defecto "hoy", muestra la fecha de la computadora).
actualizarFecha();
formulario.addEventListener("submit", guardar);
consultar();