/**
 * https://github.com/vincaslt/vscode-highlight-matching-tag (MIT, Vincas Stonys)
 */

const vscode = require('vscode')

const CONFIG = {
  color: 'yellow',
  showRuler: true,
  debounceMs: 40,
  // Archivos mas grandes (en caracteres) no se analizan
  maxChars: 1000000,
  languages: new Set([
    'html',
    'xml',
    'xsl',
    'javascript',
    'javascriptreact',
    'typescriptreact'
  ]),
  // Etiquetas HTML sin cierre
  emptyElements: new Set([
    'area',
    'base',
    'br',
    'col',
    'embed',
    'hr',
    'img',
    'input',
    'keygen',
    'link',
    'meta',
    'param',
    'source',
    'track',
    'wbr'
  ])
}

// Comentarios | etiqueta de cierre | etiqueta de apertura (con atributos)
// Los atributos admiten "..." '...' {...} (JSX, hasta 2 niveles) y => sin cortar la etiqueta
const TAG_RE =
  /<!--[\s\S]*?-->|<\/([A-Za-z][\w.:-]*)\s*>|<([A-Za-z][\w.:-]*)((?:"[^"]*"|'[^']*'|\{(?:[^{}]|\{[^{}]*\})*\}|=>|[^>"'])*?)(\/?)>/g

/**
 * Devuelve todas las etiquetas en orden de aparicion (ya ordenadas por `start`).
 * Cada una: { start, end, nameStart, nameEnd, other }
 * `other` es la etiqueta pareja (apertura <-> cierre) o null si no tiene.
 */
function parseTags(text) {
  const tags = []
  const stack = []
  TAG_RE.lastIndex = 0

  let m
  while ((m = TAG_RE.exec(text)) !== null) {
    const start = m.index
    const end = start + m[0].length

    if (m[1] !== undefined) {
      const name = m[1]
      const close = {
        start,
        end,
        nameStart: start + 2,
        nameEnd: start + 2 + name.length,
        other: null
      }
      tags.push(close)

      // Busca la apertura mas cercana con el mismo nombre
      for (let i = stack.length - 1; i >= 0; i--) {
        if (stack[i].name === name) {
          close.other = stack[i].tag
          stack[i].tag.other = close
          stack.length = i // descarta las abiertas sin cerrar que quedaron encima
          break
        }
      }
    } else if (m[2] !== undefined) {
      const name = m[2]
      if (m[4] === '/' || CONFIG.emptyElements.has(name.toLowerCase())) continue

      const open = {
        start,
        end,
        nameStart: start + 1,
        nameEnd: start + 1 + name.length,
        other: null
      }
      tags.push(open)
      stack.push({ name, tag: open })
    }
  }
  return tags
}

// Las etiquetas no se solapan, asi que hay a lo sumo una que contenga el offset:
// busqueda binaria de la ultima con start < offset
function findTag(tags, offset) {
  let lo = 0
  let hi = tags.length - 1
  let found = -1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (tags[mid].start < offset) {
      found = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  const tag = found >= 0 ? tags[found] : undefined
  return tag && tag.other && offset < tag.end ? tag : undefined
}

let decoration
let lastEditor
let lastKey = ''
let timer
let cache = { key: '', tags: [] }

function getTags(document) {
  const key = `${document.uri.toString()}@${document.version}`
  if (cache.key !== key) {
    const text = document.getText()
    cache = {
      key,
      tags: text.length > CONFIG.maxChars ? [] : parseTags(text)
    }
  }
  return cache.tags
}

function update(editor) {
  if (lastEditor && lastEditor !== editor) {
    lastEditor.setDecorations(decoration, [])
    lastKey = ''
  }
  lastEditor = editor
  if (!editor) return

  const { document } = editor

  // Offsets [inicio, fin] de los nombres a resaltar, de a pares
  const offsets = []
  if (CONFIG.languages.has(document.languageId)) {
    const tags = getTags(document)
    for (const sel of editor.selections) {
      const tag = findTag(tags, document.offsetAt(sel.active))
      if (tag) {
        offsets.push(tag.nameStart, tag.nameEnd)
        offsets.push(tag.other.nameStart, tag.other.nameEnd)
      }
    }
  }

  // Si nada cambio, no se vuelve a llamar a setDecorations
  const key = `${document.version}:${offsets}`
  if (key === lastKey) return
  lastKey = key

  const ranges = []
  for (let i = 0; i < offsets.length; i += 2) {
    ranges.push(
      new vscode.Range(
        document.positionAt(offsets[i]),
        document.positionAt(offsets[i + 1])
      )
    )
  }
  editor.setDecorations(decoration, ranges)
}

// Agrupa eventos seguidos (escribir, mantener una flecha) en una sola actualizacion
function scheduleUpdate() {
  clearTimeout(timer)
  timer = setTimeout(
    () => update(vscode.window.activeTextEditor),
    CONFIG.debounceMs
  )
}

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  decoration = vscode.window.createTextEditorDecorationType({
    borderStyle: 'solid',
    borderColor: CONFIG.color,
    borderWidth: '0 0 1px 0',
    ...(CONFIG.showRuler && {
      overviewRulerColor: CONFIG.color,
      overviewRulerLane: vscode.OverviewRulerLane.Center
    })
  })

  context.subscriptions.push(
    decoration,
    { dispose: () => clearTimeout(timer) },
    vscode.window.onDidChangeTextEditorSelection((e) => {
      if (e.textEditor === vscode.window.activeTextEditor) scheduleUpdate()
    }),
    vscode.window.onDidChangeActiveTextEditor(scheduleUpdate),
    vscode.workspace.onDidChangeTextDocument((e) => {
      const editor = vscode.window.activeTextEditor
      if (editor && e.document === editor.document) scheduleUpdate()
    })
  )

  update(vscode.window.activeTextEditor)
}

function deactivate() {
  cache = { key: '', tags: [] }
}

module.exports = {
  activate,
  deactivate
}
