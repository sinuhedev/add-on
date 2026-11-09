/**
 * https://github.com/vincaslt/vscode-highlight-matching-tag (MIT, Vincas Stonys)
 */

const vscode = require('vscode')

const CONFIG = {
  color: 'yellow',
  showRuler: true,
  languages: new Set([
    'html',
    'xml',
    'xsl',
    'vue',
    'svelte',
    'php',
    'handlebars',
    'razor',
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
 * Devuelve la lista de pares { open, close } con los offsets de cada etiqueta.
 * Cada etiqueta: { start, end, nameStart, nameEnd }
 */
function parseTags(text) {
  const pairs = []
  const stack = []
  TAG_RE.lastIndex = 0

  let m
  while ((m = TAG_RE.exec(text)) !== null) {
    const start = m.index
    const end = start + m[0].length

    if (m[1] !== undefined) {
      // Cierre: busca la apertura mas cercana con el mismo nombre
      const name = m[1]
      for (let i = stack.length - 1; i >= 0; i--) {
        if (stack[i].name === name) {
          const close = {
            start,
            end,
            nameStart: start + 2,
            nameEnd: start + 2 + name.length
          }
          pairs.push({ open: stack[i].tag, close })
          stack.length = i // descarta las abiertas sin cerrar que quedaron encima
          break
        }
      }
    } else if (m[2] !== undefined) {
      const name = m[2]
      const selfClosing = m[4] === '/'
      if (selfClosing || CONFIG.emptyElements.has(name.toLowerCase())) continue
      stack.push({
        name,
        tag: {
          start,
          end,
          nameStart: start + 1,
          nameEnd: start + 1 + name.length
        }
      })
    }
  }
  return pairs
}

// Par mas interno cuya apertura o cierre contiene el offset
function findPair(pairs, offset) {
  let best
  for (const pair of pairs) {
    for (const tag of [pair.open, pair.close]) {
      if (
        offset > tag.start &&
        offset < tag.end &&
        (!best || tag.start > best.start)
      ) {
        best = { start: tag.start, pair }
      }
    }
  }
  return best && best.pair
}

let decoration
let lastEditor
let cache = { key: '', pairs: [] }

function getPairs(document) {
  const key = `${document.uri.toString()}@${document.version}`
  if (cache.key !== key) {
    cache = { key, pairs: parseTags(document.getText()) }
  }
  return cache.pairs
}

function update(editor) {
  if (lastEditor && lastEditor !== editor) {
    lastEditor.setDecorations(decoration, [])
  }
  lastEditor = editor
  if (!editor) return

  const { document } = editor
  if (!CONFIG.languages.has(document.languageId)) {
    editor.setDecorations(decoration, [])
    return
  }

  const pairs = getPairs(document)
  const ranges = []
  for (const sel of editor.selections) {
    const pair = findPair(pairs, document.offsetAt(sel.active))
    if (!pair) continue
    for (const tag of [pair.open, pair.close]) {
      ranges.push(
        new vscode.Range(
          document.positionAt(tag.nameStart),
          document.positionAt(tag.nameEnd)
        )
      )
    }
  }
  editor.setDecorations(decoration, ranges)
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
    vscode.window.onDidChangeTextEditorSelection((e) => {
      if (e.textEditor === vscode.window.activeTextEditor) update(e.textEditor)
    }),
    vscode.window.onDidChangeActiveTextEditor(update),
    vscode.workspace.onDidChangeTextDocument((e) => {
      const editor = vscode.window.activeTextEditor
      if (editor && e.document === editor.document) update(editor)
    })
  )

  update(vscode.window.activeTextEditor)
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
}
