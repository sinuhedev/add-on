const vscode = require('vscode')

function activate(context) {
  const comando = vscode.commands.registerCommand('holaMundo.saludar', () => {
    vscode.window.showInformationMessage('¡Hola Mundo desde mi extensión!')
  })

  context.subscriptions.push(comando)
}

function deactivate() {}

module.exports = { activate, deactivate }
