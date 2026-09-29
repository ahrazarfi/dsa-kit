const vscode = require('vscode');
const fs = require('fs');
const os = require('os');
const path = require('path');

// `new` writes a problem folder path into ~/.dsa/open-request (outside any workspace, and in the same
// environment as the window: WSL home for a WSL window). This watches it and lays out:
// solution.py | input.txt / output.txt, then empties the file so `new` knows it was handled.
const REQUEST_DIR = path.join(os.homedir(), '.dsa');
const REQUEST_NAME = 'open-request';

async function handle() {
  // several windows may be open; only the one you are working in reacts
  if (!vscode.window.state.focused) return;
  const file = path.join(REQUEST_DIR, REQUEST_NAME);
  let dir;
  try { dir = fs.readFileSync(file, 'utf8').trim(); } catch { return; }
  if (!dir || !fs.existsSync(path.join(dir, 'solution.py'))) return;
  fs.writeFileSync(file, '');

  await vscode.commands.executeCommand('workbench.action.closeAllEditors');
  await vscode.commands.executeCommand('vscode.setEditorLayout', {
    orientation: 0,
    groups: [{ size: 0.5 }, { size: 0.5, groups: [{}, {}] }],
  });
  const open = async (name, col, focus) => {
    const doc = await vscode.workspace.openTextDocument(path.join(dir, name));
    await vscode.window.showTextDocument(doc, { viewColumn: col, preserveFocus: !focus });
  };
  await open('input.txt', 2, false);
  await open('output.txt', 3, false);
  await open('solution.py', 1, true);
}

function activate(context) {
  fs.mkdirSync(REQUEST_DIR, { recursive: true });
  let timer;
  const watcher = fs.watch(REQUEST_DIR, (_event, name) => {
    if (name && name !== REQUEST_NAME) return;
    clearTimeout(timer);
    timer = setTimeout(handle, 50);
  });
  context.subscriptions.push({ dispose: () => watcher.close() });
}
exports.activate = activate;
