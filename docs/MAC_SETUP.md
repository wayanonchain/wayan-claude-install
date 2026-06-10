# Mac Setup — Connecting to Your Agents

> **Key idea:** your **Mac is the control machine** — you use it to connect to
> and manage the server. The **agents (Jupiter & Uran) do not run on your Mac.**
> They run on an **Ubuntu VPS** (a rented Linux server). You install and operate
> them *over SSH* from your Mac.

```
Your Mac  ──SSH──▶  Ubuntu VPS  ──runs──▶  Jupiter + Uran (Telegram agents)
(control)           (where agents live)
```

Nothing in this repo runs your agents locally. The Mac just needs `git` and
`ssh` to reach the VPS.

---

## 1. Check you have the basics

macOS ships with both tools. Open **Terminal** and run:

```bash
git --version     # e.g. git version 2.39.x
ssh -V            # e.g. OpenSSH_9.x
```

If `git` is missing, macOS will offer to install the Command Line Tools — accept,
or run `xcode-select --install`.

---

## 2. Connect to the VPS (first time — password)

When you create a VPS, the provider gives you a **server IP** and a **root
password**. Connect with:

```bash
ssh root@SERVER_IP
```

Type the password when prompted (it won't show as you type). Replace
`SERVER_IP` with your real address (e.g. `203.0.113.10`). The first time, accept
the host fingerprint by typing `yes`.

> Password login works, but an **SSH key** (next step) is safer and means you
> never type the password again.

---

## 3. Create an SSH key (recommended)

An SSH key is a pair of files: a **private** key (stays on your Mac, secret) and
a **public** key (you copy to the server). Create one:

```bash
ssh-keygen -t ed25519
```

Press Enter to accept the default path (`~/.ssh/id_ed25519`). A passphrase is
optional but recommended. Then show the **public** key:

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy that whole line and add it to the server (paste it into your VPS provider's
"SSH keys" box when creating the server, or append it to
`/root/.ssh/authorized_keys` on the VPS). After that, `ssh root@SERVER_IP`
connects with no password.

> 🔑 **The SSH key is yours, the operator's.** It identifies *you* to *your*
> server. It is **not** part of Wayan, is **never** committed to this repo, and
> should **never** be shared. Treat `~/.ssh/id_ed25519` (the private key) like a
> password.

---

## 4. Make connecting easy — `~/.ssh/config`

Create or edit `~/.ssh/config` on your Mac and add:

```sshconfig
Host wayan-vps
    HostName SERVER_IP
    User root
    IdentityFile ~/.ssh/id_ed25519
```

Now you can connect with just:

```bash
ssh wayan-vps
```

…and the installer one-liner becomes easy to run over that connection.

---

## 5. (Optional) Cursor / VS Code Remote-SSH

If you prefer an editor over the terminal:

1. Install **VS Code** (or **Cursor**) and the **Remote - SSH** extension.
2. Open the command palette → **Remote-SSH: Connect to Host…** → pick
   `wayan-vps` (it reads your `~/.ssh/config`).
3. A new window opens *on the VPS* — you can browse files and use the integrated
   terminal there, exactly as if you were on the server.

This is handy for editing `/etc/wayan-*.env` or viewing logs, but everything is
also doable from a plain `ssh` terminal.

---

## 6. If Homebrew isn't installed

You **don't need Homebrew** for the basic flow — `git` and `ssh` come with macOS.
Homebrew is only useful for extra local tools (e.g. the `gh` GitHub CLI). If you
want it:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then, optionally: `brew install gh`. Again — optional, not required to install or
run the agents.

---

## Next

Once you can `ssh` into the VPS, follow the main
[README](../README.md#getting-started) — "Mac user → VPS install" path. The
agents are installed and run entirely on the server; your Mac just drives it.
