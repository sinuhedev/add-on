const multiwindows = require('./lib/multiwindows-highlight')
const filesizeHoverExplorer = require('./lib/filesize-hover-explorer')
const matchingTag = require('./lib/highlight-matching-tag')

function activate(context) {
  multiwindows.activate(context)
  filesizeHoverExplorer.activate(context)
  matchingTag.activate(context)
}

function deactivate() {
  multiwindows.deactivate()
  filesizeHoverExplorer.deactivate()
  matchingTag.deactivate()
}

module.exports = { activate, deactivate }
