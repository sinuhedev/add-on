const vscode = require("vscode");

function activate(context) {
	const comando = vscode.commands.registerCommand("vscode", () => {
		vscode.window.showInformationMessage("vscode..");
	});

	context.subscriptions.push(comando);
}

function deactivate() {}

module.exports = { activate, deactivate };
