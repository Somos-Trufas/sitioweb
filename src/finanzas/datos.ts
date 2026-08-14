import bruto from '../data/movimientos.json'

export type Flujo = 'Ingreso' | 'Egreso'

export interface Movimiento {
  id: string
  fecha: string
  proyecto: string
  flujo: Flujo
  categoria: string
  concepto: string
  contraparte: string
  montoUSD: number
  revisar: boolean
  motivoRevision?: string
  lineaOrigen: number
}

export interface Libro {
  generado: string
  fuente: string
  saldoInicial: number
  totales: {
    ingresos: number
    egresos: number
    saldoActual: number
    movimientos: number
    porRevisar: number
  }
  movimientos: Movimiento[]
  avisos: { linea: number; tipo: string; mensaje: string }[]
}

export const libro = bruto as Libro

export const CATEGORIAS_BENEFICAS = ['Causa benéfica']

const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

export const mesDe = (fecha: string) => fecha.slice(0, 7)

export function etiquetaMes(clave: string) {
  const [a, m] = clave.split('-')
  return `${MESES_CORTOS[Number(m) - 1]} ${a.slice(2)}`
}

export const usd = (n: number) =>
  n.toLocaleString('es', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

export const usdExacto = (n: number) =>
  n.toLocaleString('es', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })

/** Devuelve todos los meses entre el primero y el último con datos, sin huecos. */
export function rangoDeMeses(movimientos: Movimiento[]): string[] {
  if (!movimientos.length) return []
  const claves = movimientos.map((m) => mesDe(m.fecha)).sort()
  const [inicio, fin] = [claves[0], claves.at(-1)!]
  const meses: string[] = []
  let [a, m] = inicio.split('-').map(Number)
  const [aFin, mFin] = fin.split('-').map(Number)
  while (a < aFin || (a === aFin && m <= mFin)) {
    meses.push(`${a}-${String(m).padStart(2, '0')}`)
    if (++m > 12) {
      m = 1
      a++
    }
  }
  return meses
}

export interface FilaMes {
  mes: string
  etiqueta: string
  ingresos: number
  egresos: number
  neto: number
  saldo: number
}

export function serieMensual(movimientos: Movimiento[], saldoInicial: number): FilaMes[] {
  const meses = rangoDeMeses(movimientos)
  const acumulado = new Map<string, { ingresos: number; egresos: number }>()
  for (const mes of meses) acumulado.set(mes, { ingresos: 0, egresos: 0 })

  for (const m of movimientos) {
    const bucket = acumulado.get(mesDe(m.fecha))
    if (!bucket) continue
    if (m.flujo === 'Ingreso') bucket.ingresos += m.montoUSD
    else bucket.egresos += m.montoUSD
  }

  let saldo = saldoInicial
  return meses.map((mes) => {
    const { ingresos, egresos } = acumulado.get(mes)!
    const neto = ingresos - egresos
    saldo += neto
    return {
      mes,
      etiqueta: etiquetaMes(mes),
      ingresos: Number(ingresos.toFixed(2)),
      egresos: Number(egresos.toFixed(2)),
      neto: Number(neto.toFixed(2)),
      saldo: Number(saldo.toFixed(2)),
    }
  })
}

export function agrupar(
  movimientos: Movimiento[],
  clave: (m: Movimiento) => string,
): { nombre: string; monto: number }[] {
  const mapa = new Map<string, number>()
  for (const m of movimientos) mapa.set(clave(m), (mapa.get(clave(m)) ?? 0) + m.montoUSD)
  return [...mapa]
    .map(([nombre, monto]) => ({ nombre, monto: Number(monto.toFixed(2)) }))
    .sort((a, b) => b.monto - a.monto)
}

export interface FilaProyecto {
  proyecto: string
  ingresos: number
  egresos: number
  neto: number
}

export function porProyecto(movimientos: Movimiento[]): FilaProyecto[] {
  const mapa = new Map<string, { ingresos: number; egresos: number }>()
  for (const m of movimientos) {
    const fila = mapa.get(m.proyecto) ?? { ingresos: 0, egresos: 0 }
    if (m.flujo === 'Ingreso') fila.ingresos += m.montoUSD
    else fila.egresos += m.montoUSD
    mapa.set(m.proyecto, fila)
  }
  return [...mapa]
    .map(([proyecto, v]) => ({
      proyecto,
      ingresos: Number(v.ingresos.toFixed(2)),
      egresos: Number(v.egresos.toFixed(2)),
      neto: Number((v.ingresos - v.egresos).toFixed(2)),
    }))
    .sort((a, b) => b.ingresos + b.egresos - (a.ingresos + a.egresos))
}
