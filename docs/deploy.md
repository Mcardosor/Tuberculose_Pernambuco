# Deploy — VM dos painéis

| | |
|---|---|
| Público | `https://painel.cenarios.unb.br/cenarios/tbpe/` |
| Direto, por VPN | `http://10.20.10.64:8504/cenarios/tbpe/` |
| Pasta na VM | `~/tbpe` |
| Dados | volume de `~/dashboard-sinan-pe/data` — a mesma extração do painel nacional; nada é copiado |

Este painel **substitui** o `tbpe` da geração anterior (Superset +
`dados_dashboard/`), que está no ar no mesmo caminho e na mesma porta. Na
primeira subida, pare aquele antes — o `container_name` é o mesmo e a porta
também:

```bash
ssh cenarios-vm 'cd ~/tbpe && docker compose down && mv ~/tbpe ~/tbpe-superset'
ssh cenarios-vm 'git clone <remoto> ~/tbpe && cd ~/tbpe && SINAN_DATA_DIR=~/dashboard-sinan-pe/data docker compose up -d --build'
```

Nas seguintes:

```bash
ssh cenarios-vm 'cd ~/tbpe && git pull && docker compose up -d --build'
```

Localmente, com a junção `data -> ../sinan/data`:

```bash
SINAN_DATA_DIR=./data docker compose up -d --build
```

No Git Bash, `-v /app/data` vira `C:/Program Files/Git/app/data` e o volume
não monta — o container fica `healthy` com `FileNotFoundError` na página.
Rode com `MSYS_NO_PATHCONV=1`, ou pelo PowerShell.

## O bloco do nginx

A acrescentar em `/etc/nginx/sites-enabled/telessaude`, junto dos outros
`location`. **Sem barra final** nos dois lados — o Streamlit roda com
`--server.baseUrlPath=cenarios/tbpe` e espera o prefixo.

```nginx
    location /cenarios/tbpe {
        proxy_pass         http://localhost:8504;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection $connection_upgrade;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Depois de todo deploy

O healthcheck não sabe se a aplicação funciona — `/_stcore/health` responde
mesmo com o script quebrado. Abra a página e confira um número conhecido:
**PE 2024, incidência 55,00 e 5.246 casos novos**; clique na macro
Metropolitana e os cards têm de mudar para 73,80 e 4.150.
