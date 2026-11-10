const multiwindows = require('./lib/multiwindows-highlight')
const filesizeHoverExplorer = require('./lib/filesize-hover-explorer')
const matchingTag = require('./lib/highlight-matching-tag')
const css = require('./lib/css')

function activate(context) {
  multiwindows.activate(context)
  filesizeHoverExplorer.activate(context)
  matchingTag.activate(context)
  css.activate(context)
}

function deactivate() {
  multiwindows.deactivate()
  filesizeHoverExplorer.deactivate()
  matchingTag.deactivate()
  css.deactivate()
}

module.exports = { activate, deactivate }
