# Install

```
conda create --prefix .conda/ python==3.7
conda activate .conda/
pip install -e .
```

# Run

```
conda activate .conda/
tensorhive --log-level=debug
```

# Generate ssh key

Changing key to ed25519 instead of rsa is necessary to connect to 8.8+ ssh server

ssh-keygen -t ed25519 -f ssh_key

and copy to ~/.config/Tensorhive/ssh_key
and copy pub key to hosts in /home/tensorhive/.ssh/authorized_keys