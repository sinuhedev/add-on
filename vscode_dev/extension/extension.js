const vscode = require('vscode')
const multiwindows = require('./lib/multiwindows-highlight')

function activate(context) {
  const comando = vscode.commands.registerCommand('holaMundo.saludar', () => {
    vscode.window.showInformationMessage('¡Hola Mundo desde mi extensión!')
  })
  context.subscriptions.push(comando)

  multiwindows.activate(context)
}

function deactivate() {
  multiwindows.deactivate()
}

module.exports = { activate, deactivate }
