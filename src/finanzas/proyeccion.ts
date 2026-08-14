import { type FilaMes, type Movimiento, etiquetaMes, mesDe } from './datos'

/**
 * Proyección a 6 meses.
 *
 * Deliberadamente simple. Con ~530 movimientos en dos años y una estacionalidad
 * que depende de cuándo se organiza un torneo, una regresión sofisticada daría
 * una precisión falsa. El método acá es el que un tesorero puede defender frente
 * a un patrocinador:
 *
 *   egreso proyectado = gasto recurrente conocido (determinista)
 *                     + media móvil de 3 meses del gasto variable
 *   ingreso proyectado = media móvil de 3 meses
 *   banda              = ±1 desvío estándar de los últimos 6 meses
 *
 * El gasto recurrente se detecta, no se codifica a mano: una contraparte que
 * cobró en al menos la mitad de los últimos 12 meses es una suscripción.
 */

export const HORIZONTE_MESES = 6
const VENTANA_MEDIA_MOVIL = 3
const VENTANA_VOLATILIDAD = 6
const MESES_RECURRENCIA = 12

export interface FilaProyectada {
  mes: string
  etiqueta: string
  proyectado: true
  saldoBase: number
  saldoOptimista: number
  saldoPesimista: number
  /** Recharts dibuja el área de banda a partir de [piso, techo]. */
  banda: [number, number]
}

export interface FilaHistorica extends FilaMes {
  proyectado: false
}

export type PuntoProyeccion = (FilaHistorica | FilaProyectada) & { saldoBase?: number }

export interface Recurrente {
  contraparte: string
  mensual: number
  mesesActivo: number
}

export interface Proyeccion {
  puntos: PuntoProyeccion[]
  recurrentes: Recurrente[]
  gastoFijoMensual: number
  gastoVariableMensual: number
  ingresoMensual: number
  volatilidad: number
  runwayMeses: number | null
}

const promedio = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0)

function desvioEstandar(xs: number[]) {
  if (xs.length < 2) return 0
  const mu = promedio(xs)
  return Math.sqrt(promedio(xs.map((x) => (x - mu) ** 2)))
}

function siguienteMes(clave: string) {
  let [a, m] = clave.split('-').map(Number)
  if (++m > 12) {
    m = 1
    a++
  }
  return `${a}-${String(m).padStart(2, '0')}`
}

/**
 * Contrapartes de egreso presentes en al menos la mitad de los últimos N meses.
 * Devuelve el gasto mensual promedio de cada una.
 */
export function detectarRecurrentes(
  movimientos: Movimiento[],
  mesesRecientes: string[],
): Recurrente[] {
  const ventana = new Set(mesesRecientes.slice(-MESES_RECURRENCIA))
  if (!ventana.size) return []

  const porContraparte = new Map<string, Map<string, number>>()
  for (const m of movimientos) {
    if (m.flujo !== 'Egreso') continue
    const mes = mesDe(m.fecha)
    if (!ventana.has(mes)) continue
    const meses = porContraparte.get(m.contraparte) ?? new Map<string, number>()
    meses.set(mes, (meses.get(mes) ?? 0) + m.montoUSD)
    porContraparte.set(m.contraparte, meses)
  }

  const umbral = Math.ceil(ventana.size / 2)
  return [...porContraparte]
    .filter(([, meses]) => meses.size >= umbral)
    .map(([contraparte, meses]) => ({
      contraparte,
      // Se divide por el tamaño de la ventana, no por los meses con cobro:
      // un servicio que se saltó un mes cuesta menos por mes, no lo mismo.
      mensual: Number(([...meses.values()].reduce((a, b) => a + b, 0) / ventana.size).toFixed(2)),
      mesesActivo: meses.size,
    }))
    .sort((a, b) => b.mensual - a.mensual)
}

export function proyectar(historico: FilaMes[], movimientos: Movimiento[]): Proyeccion {
  const meses = historico.map((f) => f.mes)
  const recurrentes = detectarRecurrentes(movimientos, meses)
  const gastoFijoMensual = Number(recurrentes.reduce((s, r) => s + r.mensual, 0).toFixed(2))

  const ultimos = historico.slice(-VENTANA_MEDIA_MOVIL)
  const ingresoMensual = Number(promedio(ultimos.map((f) => f.ingresos)).toFixed(2))
  const egresoMensual = Number(promedio(ultimos.map((f) => f.egresos)).toFixed(2))
  // El gasto fijo es un piso: si la media móvil quedó por debajo, el variable es cero.
  const gastoVariableMensual = Number(Math.max(0, egresoMensual - gastoFijoMensual).toFixed(2))

  const netosRecientes = historico.slice(-VENTANA_VOLATILIDAD).map((f) => f.neto)
  const volatilidad = Number(desvioEstandar(netosRecientes).toFixed(2))

  const historicos: FilaHistorica[] = historico.map((f) => ({ ...f, proyectado: false }))

  const saldoFinal = historico.at(-1)?.saldo ?? 0
  const netoMensual = ingresoMensual - (gastoFijoMensual + gastoVariableMensual)

  const proyectados: FilaProyectada[] = []
  let mes = historico.at(-1)?.mes ?? new Date().toISOString().slice(0, 7)
  let base = saldoFinal
  let optimista = saldoFinal
  let pesimista = saldoFinal

  for (let i = 0; i < HORIZONTE_MESES; i++) {
    mes = siguienteMes(mes)
    base += netoMensual
    optimista += netoMensual + volatilidad
    pesimista += netoMensual - volatilidad
    proyectados.push({
      mes,
      etiqueta: etiquetaMes(mes),
      proyectado: true,
      saldoBase: Number(base.toFixed(2)),
      saldoOptimista: Number(optimista.toFixed(2)),
      saldoPesimista: Number(pesimista.toFixed(2)),
      banda: [Number(pesimista.toFixed(2)), Number(optimista.toFixed(2))],
    })
  }

  // Meses hasta quedarse sin fondos al ritmo actual. Solo tiene sentido si el
  // neto es negativo; con neto positivo la organización no se está consumiendo.
  const runwayMeses = netoMensual < 0 ? Math.max(0, saldoFinal / -netoMensual) : null

  // El primer punto proyectado se ancla al último real para que la línea no salte.
  const puente = historicos.at(-1)
  const puntos: PuntoProyeccion[] = [
    ...historicos,
    ...proyectados.map((p, i) =>
      i === 0 && puente
        ? p
        : p,
    ),
  ]

  return {
    puntos,
    recurrentes,
    gastoFijoMensual,
    gastoVariableMensual,
    ingresoMensual,
    volatilidad,
    runwayMeses,
  }
}
