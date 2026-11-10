const vscode = require('vscode')
const fs = require('fs/promises')
const { constants } = require('fs')
const path = require('path')
const crypto = require('crypto')

const START = '<!-- MI-CUSTOM-CSS-START -->'
const END = '<!-- MI-CUSTOM-CSS-END -->'

const CUSTOM_CSS = `

.part.sidebar.left > .header {
  display: none !important;
}

.part.sidebar.left > .composite > .title-actions {
  display: none !important;
}

.watermark-container{
    display: none !important;
}

`

const BLOCK = `\n${START}\n<style>\n${CUSTOM_CSS}\n</style>\n${END}\n`
const INJECTED_RE = new RegExp(`\\n?${START}[\\s\\S]*?${END}\\n?`, 'g')

const APP_ROOT = vscode.env.appRoot
const OUT_DIR = path.join(APP_ROOT, 'out')
const PRODUCT_PATH = path.join(APP_ROOT, 'product.json')

const exists = (p) =>
  fs.access(p).then(
    () => true,
    () => false
  )

// Copia de respaldo solo si todavía no existe.
async function backup(file) {
  try {
    await fs.copyFile(
      file,
      `${file}.mi-custom-css.bak`,
      constants.COPYFILE_EXCL
    )
  } catch (err) {
    if (err.code !== 'EEXIST') throw err
  }
}

async function findWorkbenchHtml() {
  for (const dir of ['electron-sandbox', 'electron-browser']) {
    const file = path.join(
      OUT_DIR,
      'vs',
      'code',
      dir,
      'workbench',
      'workbench.html'
    )
    if (await exists(file)) return file
  }
}

// Actualiza el checksum de workbench.html en product.json para evitar el aviso
// "installation appears to be corrupt". Devuelve true si cambió algo.
async function fixChecksum() {
  let raw
  try {
    raw = await fs.readFile(PRODUCT_PATH, 'utf8')
  } catch {
    return false
  }

  const { checksums = {} } = JSON.parse(raw)
  let changed = false

  for (const [key, oldHash] of Object.entries(checksums)) {
    if (!key.endsWith('workbench.html')) continue

    let data
    try {
      data = await fs.readFile(path.join(OUT_DIR, ...key.split('/')))
    } catch {
      continue
    }

    const hash = crypto
      .createHash('sha256')
      .update(data)
      .digest('base64')
      .replace(/=+$/, '')

    if (hash !== oldHash) {
      // Reemplazo directo sobre el texto: conserva el formato original del archivo.
      raw = raw.replace(`"${oldHash}"`, () => `"${hash}"`)
      changed = true
    }
  }

  if (changed) {
    await backup(PRODUCT_PATH)
    await fs.writeFile(PRODUCT_PATH, raw, 'utf8')
  }
  return changed
}

function handleError(err) {
  const msg =
    err && (err.code === 'EACCES' || err.code === 'EPERM')
      ? 'Mi Custom CSS: sin permisos para modificar los archivos de VS Code. ' +
        'Ábrelo como administrador (Windows) o ajusta permisos con chown/sudo (Linux/Mac) sobre la carpeta de instalación.'
      : `Mi Custom CSS: ${err.message || err}`
  vscode.window.showErrorMessage(msg)
}

async function apply() {
  try {
    const htmlPath = await findWorkbenchHtml()
    if (!htmlPath) {
      throw new Error(
        'No se encontró workbench.html en esta versión de VS Code.'
      )
    }

    const current = await fs.readFile(htmlPath, 'utf8')
    const htmlChanged = !current.includes(BLOCK)

    if (htmlChanged) {
      await backup(htmlPath)
      const html = current
        .replace(INJECTED_RE, '\n')
        .replace('</html>', () => `${BLOCK}</html>`)
      await fs.writeFile(htmlPath, html, 'utf8')
    }

    // Se ejecuta siempre: corrige también un checksum desfasado de arranques anteriores.
    const checksumChanged = await fixChecksum()

    if (htmlChanged || checksumChanged) {
      vscode.window.showInformationMessage(
        'Mi Custom CSS aplicado. Cierra VS Code por completo y ábrelo de nuevo para ver los cambios.'
      )
    }
  } catch (err) {
    handleError(err)
  }
}

function activate() {
  return apply()
}

function deactivate() {}

module.exports = { activate, deactivate }
