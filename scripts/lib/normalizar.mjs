import { createHash } from 'node:crypto'

/**
 * Normaliza el CSV de la hoja «Contabilidad Financiera» al esquema de la
 * plantilla Contabilidad_Somos_Trufas.
 *
 * La hoja de origen tiene tres particularidades que hay que deshacer acá:
 *   1. El signo vive en el monto («-$5,00») y además en la columna Flujo.
 *      Nos quedamos con Flujo como única fuente de dirección.
 *   2. Los montos son texto con coma decimal y separador de miles opcional.
 *   3. Las columnas 7..13 llevan totales sueltos incrustados en filas de datos.
 *      Se ignoran: el dashboard recalcula todo desde los movimientos.
 */

export const CATEGORIAS_EGRESO = [
  'Causa benéfica',
  'Premiación',
  'Producción de evento',
  'Infraestructura',
  'Comisiones y divisas',
  'Software',
  'Marketing',
  'Administrativo',
  'Retribución',
  'Otros',
]

export const CATEGORIAS_INGRESO = [
  'Donación',
  'Patrocinio',
  'Inscripción',
  'Aporte interno',
  'Ajuste',
]

export const SIN_CLASIFICAR = 'Sin clasificar'

export const PROYECTOS = ['Comunidad', 'Esports', 'Circuitos', 'General']

/**
 * Entidades que representan al staff de la organización, no a terceros.
 * Un egreso de «Evento» hacia ellas es pago de trabajo, no premio.
 */
const ENTIDADES_STAFF = new Set(['Personal'])

/**
 * Entidades genéricas que no identifican a nadie en concreto. Un egreso hacia
 * «Usuario» no se puede clasificar sin mirar el comprobante.
 */
const ENTIDADES_OPACAS = new Set(['Usuario', 'Varios'])

/** Motivo original -> categoría nueva, cuando el mapeo no depende del contexto. */
const MAPEO_DIRECTO = {
  Caridad: 'Causa benéfica',
  Retribución: 'Retribución',
  'Discord Bot': 'Infraestructura',
  Hosting: 'Infraestructura',
  Comisiones: 'Comisiones y divisas',
  Reembolso: 'Otros',
  Patrocinio: 'Patrocinio',
}

/**
 * Decide la categoría nueva. Devuelve `revisar` cuando la fila original no
 * tiene información suficiente para clasificarla sin criterio humano: esas
 * filas se cargan igual, pero el dashboard las muestra aparte.
 */
export function clasificar({ motivo, flujo, entidad }) {
  const directa = MAPEO_DIRECTO[motivo]
  if (directa) return { categoria: directa, revisar: false }

  if (motivo === 'Donación') {
    if (flujo === 'Ingreso') return { categoria: 'Donación', revisar: false }
    // Un egreso etiquetado «Donación» es ambiguo: ¿donamos a una causa o
    // devolvimos un aporte? Sin comprobante no se puede saber.
    return {
      categoria: SIN_CLASIFICAR,
      revisar: true,
      motivoRevision: 'Egreso etiquetado «Donación»: puede ser causa benéfica o devolución.',
    }
  }

  if (motivo === 'Evento') {
    if (flujo === 'Ingreso') return { categoria: 'Inscripción', revisar: false }
    if (ENTIDADES_STAFF.has(entidad)) return { categoria: 'Retribución', revisar: false }
    if (ENTIDADES_OPACAS.has(entidad)) {
      return {
        categoria: SIN_CLASIFICAR,
        revisar: true,
        motivoRevision: `Egreso de evento hacia «${entidad}»: falta saber si fue premio, producción o retribución.`,
      }
    }
    // Contraparte con nombre propio de equipo: es un premio.
    return { categoria: 'Premiación', revisar: false }
  }

  if (motivo === 'Personales') {
    if (entidad === 'CEO Nitro Anual') return { categoria: 'Administrativo', revisar: false }
    // Decisión de la organización (ago-2026): «Personales» son recompensas a
    // miembros de la comunidad, incluso cuando la contraparte quedó anotada de
    // forma genérica. Coincide con los exports de Notion, que registran estos
    // mismos pagos como «Recompensa».
    return { categoria: 'Premiación', revisar: false }
  }

  return {
    categoria: SIN_CLASIFICAR,
    revisar: true,
    motivoRevision: motivo ? `Motivo «${motivo}» sin mapeo definido.` : 'Fila sin motivo.',
  }
}

/** «-$1.234,56» -> 1234.56 (siempre positivo; la dirección la da Flujo). */
export function parsearMonto(texto) {
  if (!texto) return null
  const limpio = String(texto).replace(/[$\s]/g, '').replace(/\./g, '').replace(',', '.')
  const n = Number.parseFloat(limpio)
  if (!Number.isFinite(n)) return null
  return Math.abs(n)
}

/** «5/09/2024» -> «2024-09-05» */
export function parsearFecha(texto) {
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(String(texto ?? '').trim())
  if (!m) return null
  const [, d, mes, a] = m
  const dd = Number(d)
  const mm = Number(mes)
  if (mm < 1 || mm > 12 || dd < 1 || dd > 31) return null
  const iso = `${a}-${String(mm).padStart(2, '0')}-${String(dd).padStart(2, '0')}`
  // Rechaza fechas tipo 31/02 que el formato deja pasar.
  const fecha = new Date(`${iso}T00:00:00Z`)
  if (fecha.getUTCDate() !== dd || fecha.getUTCMonth() + 1 !== mm) return null
  return iso
}

/** Parser CSV mínimo con soporte de comillas dobles y CRLF. */
export function parsearCSV(texto) {
  const filas = []
  let fila = []
  let campo = ''
  let enComillas = false

  for (let i = 0; i < texto.length; i++) {
    const c = texto[i]
    if (enComillas) {
      if (c === '"') {
        if (texto[i + 1] === '"') {
          campo += '"'
          i++
        } else enComillas = false
      } else campo += c
      continue
    }
    if (c === '"') enComillas = true
    else if (c === ',') {
      fila.push(campo)
      campo = ''
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && texto[i + 1] === '\n') i++
      fila.push(campo)
      filas.push(fila)
      fila = []
      campo = ''
    } else campo += c
  }
  if (campo !== '' || fila.length) {
    fila.push(campo)
    filas.push(fila)
  }
  return filas
}

/**
 * ID estable entre sincronizaciones. Se deriva del contenido de la fila más un
 * ordinal, para que dos movimientos idénticos el mismo día no colapsen en uno.
 */
function generarId(campos, ocurrencia) {
  const hash = createHash('sha1').update(`${campos.join('|')}|${ocurrencia}`).digest('hex')
  return `TRX-${hash.slice(0, 10)}`
}

/**
 * @param {string} csv       Contenido crudo del CSV exportado del Sheet.
 * @param {object} [opts]
 * @param {string} [opts.fuente] Etiqueta de procedencia para el JSON.
 * @returns {{saldoInicial:number, movimientos:Array, avisos:Array, descartadas:Array}}
 */
export function normalizar(csv, { fuente = 'desconocida' } = {}) {
  const filas = parsearCSV(csv)
  if (!filas.length) throw new Error('El CSV está vacío.')

  const encabezado = filas[0].map((c) => c.trim())
  const esperado = ['Proyecto', 'Fecha', 'Flujo', 'Entidad', 'Motivo', 'Monto']
  const faltan = esperado.filter((c) => !encabezado.includes(c))
  if (faltan.length) {
    throw new Error(
      `El CSV no tiene las columnas esperadas. Faltan: ${faltan.join(', ')}. ` +
        `Encontradas: ${encabezado.slice(0, 6).join(', ')}`,
    )
  }
  const idx = Object.fromEntries(esperado.map((c) => [c, encabezado.indexOf(c)]))

  const movimientos = []
  const avisos = []
  const descartadas = []
  const vistos = new Map()
  let saldoInicial = 0

  filas.slice(1).forEach((fila, i) => {
    const linea = i + 2
    const campo = (nombre) => (fila[idx[nombre]] ?? '').trim()

    const proyecto = campo('Proyecto')
    const fechaCruda = campo('Fecha')
    const flujo = campo('Flujo')
    const entidad = campo('Entidad')
    const motivo = campo('Motivo')
    const montoCrudo = campo('Monto')

    // Filas separadoras de la hoja.
    if (!fechaCruda && !montoCrudo && !proyecto) return

    const fecha = parsearFecha(fechaCruda)
    const monto = parsearMonto(montoCrudo)

    if (!fecha) {
      descartadas.push({ linea, razon: `Fecha ilegible: «${fechaCruda}»`, fila: fila.slice(0, 6) })
      return
    }
    if (monto === null || monto === 0) {
      descartadas.push({ linea, razon: `Monto ilegible o cero: «${montoCrudo}»`, fila: fila.slice(0, 6) })
      return
    }

    // «Reajuste» no es un movimiento: es el saldo de apertura del libro.
    if (flujo === 'Reajuste') {
      saldoInicial += monto
      avisos.push({
        linea,
        tipo: 'saldo-inicial',
        mensaje: `Fila «Reajuste» de ${montoCrudo} tomada como saldo inicial, no como ingreso.`,
      })
      return
    }

    if (flujo !== 'Ingreso' && flujo !== 'Egreso') {
      descartadas.push({ linea, razon: `Flujo desconocido: «${flujo}»`, fila: fila.slice(0, 6) })
      return
    }

    const { categoria, revisar, motivoRevision } = clasificar({ motivo, flujo, entidad })

    const proyectoFinal = PROYECTOS.includes(proyecto) ? proyecto : 'General'
    if (!proyecto) {
      avisos.push({ linea, tipo: 'proyecto-vacio', mensaje: `Fila sin proyecto, asignada a «General».` })
    } else if (!PROYECTOS.includes(proyecto)) {
      avisos.push({
        linea,
        tipo: 'proyecto-desconocido',
        mensaje: `Proyecto «${proyecto}» fuera del catálogo, asignado a «General».`,
      })
    }

    const clave = [fecha, proyectoFinal, flujo, entidad, motivo, monto].join('|')
    const ocurrencia = (vistos.get(clave) ?? 0) + 1
    vistos.set(clave, ocurrencia)

    movimientos.push({
      id: generarId([fecha, proyectoFinal, flujo, entidad, motivo, String(monto)], ocurrencia),
      fecha,
      proyecto: proyectoFinal,
      flujo,
      categoria,
      concepto: motivo || '(sin concepto)',
      contraparte: entidad || '(sin contraparte)',
      montoUSD: Number(monto.toFixed(2)),
      revisar,
      ...(motivoRevision ? { motivoRevision } : {}),
      lineaOrigen: linea,
    })
  })

  movimientos.sort((a, b) => (a.fecha < b.fecha ? -1 : a.fecha > b.fecha ? 1 : 0))

  return { saldoInicial: Number(saldoInicial.toFixed(2)), movimientos, avisos, descartadas, fuente }
}
