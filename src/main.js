import { createClient } from "@supabase/supabase-js";
import "./style.css";

// La URL y la llave se leen de .env al iniciar o construir la aplicación.
const supabase = createClient(
  import.meta.env.SUPABASE_URL,
  import.meta.env.SUPABASE_PUBLISHABLE_KEY,
);

const formulario = document.querySelector("#registro");
const boton = formulario.querySelector("button");
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
const opcionesFecha = document.querySelectorAll('.opcion-fecha');
const inputFecha = document.querySelector("#fecha");

function actualizarFecha() {
  const tipoSeleccionado = document.querySelector('input[name="fecha-tipo"]:checked').value;
  opcionesFecha.forEach((op) => op.classList.toggle("activo", op.querySelector("input").checked));
  if (tipoSeleccionado === "hoy") {
    inputFecha.value = hoyISO();
    inputFecha.disabled = true;
  } else {
    inputFecha.disabled = false;
    if (!inputFecha.value) inputFecha.value = hoyISO();
  }
}

opcionesFecha.forEach((op) => op.querySelector("input").addEventListener("change", actualizarFecha));

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

// Consultar los registros
async function consultar() {
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
  const { fecha, parcela, cultivo, actividad, observaciones } = Object.fromEntries(new FormData(formulario));

  boton.disabled = true;
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
