/**
 * https://github.com/andrewkelden/vscode-filesize-hover-explorer
 */

const vscode = require('vscode')

const UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
const DEBOUNCE_MS = 200

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes}B`

  // Un solo calculo en vez de un bucle de divisiones
  const i = Math.min(Math.floor(Math.log2(bytes) / 10), UNITS.length - 1)
  return `${(bytes / 1024 ** i).toFixed(1)}${UNITS[i]}`
}

class FileSizeDecorationProvider {
  constructor() {
    this._emitter = new vscode.EventEmitter()
    this.onDidChangeFileDecorations = this._emitter.event
    this._pending = new Map()
    this._timer = undefined
  }

  async provideFileDecoration(uri) {
    try {
      const stat = await vscode.workspace.fs.stat(uri)
      if (stat.type & vscode.FileType.File) {
        return { tooltip: formatFileSize(stat.size) }
      }
    } catch {
      // Archivo borrado o esquema no soportado: sin decoracion
    }
  }

  // Agrupa varios cambios seguidos en un solo evento
  fileChanged(uri) {
    this._pending.set(uri.toString(), uri)
    clearTimeout(this._timer)
    this._timer = setTimeout(() => {
      const uris = [...this._pending.values()]
      this._pending.clear()
      this._emitter.fire(uris)
    }, DEBOUNCE_MS)
  }

  dispose() {
    clearTimeout(this._timer)
    this._pending.clear()
    this._emitter.dispose()
  }
}

function activate(context) {
  const provider = new FileSizeDecorationProvider()
  const watcher = vscode.workspace.createFileSystemWatcher(
    '**/*',
    true,
    false,
    true
  )

  context.subscriptions.push(
    provider,
    watcher,
    vscode.window.registerFileDecorationProvider(provider),
    watcher.onDidChange((uri) => provider.fileChanged(uri))
  )
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
}
