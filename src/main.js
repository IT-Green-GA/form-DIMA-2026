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

function mostrar(registros) {
  filas.replaceChildren();
  if (registros.length === 0) {
    const celda = filas.insertRow().insertCell();
    celda.colSpan = 8;
    celda.textContent = "Todavía no hay registros.";
    return;
  }
  for (const r of registros) {
    const fila = filas.insertRow();
    for (const valor of [formatoFecha(r.fecha), r.parcela, r.cultivo, r.actividad, r.temperatura ?? "—", r.estado ?? "—", r.responsable ?? "—", r.observaciones ?? ""]) {
      fila.insertCell().textContent = valor;
    }
  }
}

const DEMO = [
  { fecha: "2026-10-19", parcela: "P-031 San Diego",  cultivo: "Fresa",  actividad: "Observación",   temperatura: "24", estado: "Floración",    responsable: "Donaji",   observaciones: "Plantas en floración abundante. Flores blancas en el 80% de los tallos. Sin plagas visibles." },
  { fecha: "2026-10-17", parcela: "P-031 San Diego",  cultivo: "Fresa",  actividad: "Riego",         temperatura: "22", estado: "Óptimo",       responsable: "Donaji",   observaciones: "Riego por goteo, 2 horas. Suelo con humedad óptima al finalizar." },
  { fecha: "2026-10-15", parcela: "P-077 El Cerrito", cultivo: "Fresa",  actividad: "Fertilización", temperatura: "21", estado: "Crecimiento",  responsable: "Donaji",   observaciones: "Aplicación NPK 10-10-10. Dosis: 5 L por 100 m². Sin quemadura foliar." },
  { fecha: "2026-10-13", parcela: "P-012 La Loma",    cultivo: "Fresa",  actividad: "Muestreo",      temperatura: "20", estado: "Estable",      responsable: "Donaji",   observaciones: "10 muestras de suelo. pH promedio: 6.2. Materia orgánica adecuada." },
  { fecha: "2026-10-10", parcela: "P-031 San Diego",  cultivo: "Fresa",  actividad: "Observación",   temperatura: "23", estado: "Fructificación", responsable: "Donaji", observaciones: "Primeros frutos verdes. Inicio de cosecha estimado en 3 semanas." },
  { fecha: "2026-10-07", parcela: "P-077 El Cerrito", cultivo: "Maíz",   actividad: "Riego",         temperatura: "22", estado: "Óptimo",       responsable: "Donaji",   observaciones: "Riego por aspersión 90 minutos. Temperatura ambiente: 22 °C." },
  { fecha: "2026-10-04", parcela: "P-012 La Loma",    cultivo: "Frijol", actividad: "Fertilización", temperatura: "19", estado: "Crecimiento",  responsable: "Donaji",   observaciones: "Segunda fertilización del ciclo. Buen color en follaje, sin clorosis." },
];

// Consultar los registros
async function consultar() {
  const { data, error } = await supabase
    .from("registros")
    .select("*")
    .order("fecha", { ascending: false });
  if (error) {
    console.error(error);
    mostrar(DEMO);
    return;
  }
  mostrar(data.length ? data : DEMO);
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

// Fecha de hoy, en la zona horaria de la computadora.
formulario.fecha.value = new Date().toLocaleDateString("en-CA");
formulario.addEventListener("submit", guardar);
consultar();
