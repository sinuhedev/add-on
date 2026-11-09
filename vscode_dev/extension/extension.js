const multiwindows = require('./lib/multiwindows-highlight')
const filesizeHoverExplorer = require('./lib/filesize-hover-explorer')

function activate(context) {
  multiwindows.activate(context)
  filesizeHoverExplorer.activate(context)
}

function deactivate() {
  multiwindows.deactivate()
  filesizeHoverExplorer.deactivate()
}

module.exports = { activate, deactivate }
