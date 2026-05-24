# Деплой на 111.88.147.92

## 1. SSH на Mac (`~/.ssh/config`)

```
Host ts-ai-es
    HostName 111.88.147.92
    User esasim
    IdentityFile ~/.ssh/id_ed25519_agents_deploy
    IdentitiesOnly yes
```

Проверка: `ssh ts-ai-es`

## 2. Rsync с Mac

```bash
cd /Users/evgenii/Desktop/agents
chmod +x deploy/rsync-to-server.sh
./deploy/rsync-to-server.sh
```

Исключается: `.venv`, `.git`, `.env`, вся `data/` (БД переносите отдельно).

Перенос БД с Mac (один раз):

```bash
ssh ts-ai-es 'mkdir -p ~/agents/data'
rsync -avz data/leads.db ts-ai-es:~/agents/data/leads.db
```

## 3. Первый запуск на сервере

```bash
ssh ts-ai-es
cd ~/agents
chmod +x deploy/setup-server.sh
./deploy/setup-server.sh
nano .env   # YANDEX_API_KEY и др.
sudo systemctl restart tender-agents
```

## 4. Обновления

```bash
./deploy/rsync-to-server.sh
ssh ts-ai-es 'cd ~/agents && .venv/bin/pip install -e ".[web,excel]" && sudo systemctl restart tender-agents'
```

## Проверка

```bash
curl -sI http://111.88.147.92:8765/
curl -sI http://111.88.147.92/
```

После reboot: `ssh ts-ai-es 'systemctl is-active tender-agents'`
