/**
 * https://github.com/aki12n/multiwindows-highlight
 */

const vscode = require('vscode')

const CONFIG = {
  darkBackgroundColor: 'rgba(255, 255, 204, 0.3)',
  darkColor: 'yellow',
  caseInsensitive: true,
  debounceMs: 60
}

let decoration
let timer

function activate(context) {
  // Se crea una sola vez y se reutiliza
  decoration = vscode.window.createTextEditorDecorationType({
    borderWidth: '1px',
    borderStyle: 'solid',
    dark: {
      overviewRulerColor: CONFIG.darkBackgroundColor,
      backgroundColor: CONFIG.darkBackgroundColor,
      color: CONFIG.darkColor
    }
  })

  context.subscriptions.push(
    decoration,
    { dispose: () => clearTimeout(timer) },

    vscode.window.onDidChangeVisibleTextEditors(clearAll),

    vscode.window.onDidChangeTextEditorSelection(({ textEditor }) => {
      clearTimeout(timer)
      const sel = textEditor.selection
      const word = sel.isEmpty ? '' : textEditor.document.getText(sel)

      // Sin seleccion o multilinea: solo limpiar
      if (!word || word.includes('\n') || word.includes('\r')) {
        clearAll()
        return
      }
      // Debounce: evita recalcular en cada movimiento al arrastrar
      timer = setTimeout(() => highlight(word), CONFIG.debounceMs)
    })
  )
}

function clearAll() {
  for (const editor of vscode.window.visibleTextEditors) {
    editor.setDecorations(decoration, [])
  }
}

function highlight(word) {
  const needle = CONFIG.caseInsensitive ? word.toLowerCase() : word

  for (const editor of vscode.window.visibleTextEditors) {
    const doc = editor.document
    // Se busca en todo el texto de una vez (un solo indexOf por coincidencia)
    const text = doc.getText()
    const haystack = CONFIG.caseInsensitive ? text.toLowerCase() : text

    const ranges = []
    let idx = haystack.indexOf(needle)
    while (idx !== -1) {
      ranges.push(
        new vscode.Range(
          doc.positionAt(idx),
          doc.positionAt(idx + needle.length)
        )
      )
      idx = haystack.indexOf(needle, idx + needle.length)
    }
    editor.setDecorations(decoration, ranges)
  }
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
}
