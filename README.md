# Add-on

```sh
# blender_dev
ln -s $HOME/Dev/add-on/blender_dev $HOME/.config/blender/5.2/extensions/user_default

# vscode_dev
cd ~/Dev/add-on/vscode_dev && zip /tmp/vscode_dev-0.0.1.vsix -r ./* && /opt/VSCode-linux-x64/bin/code --install-extension /tmp/vscode_dev-0.0.1.vsix 

```
