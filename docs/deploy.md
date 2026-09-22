# Deploy — VM dos painéis

| | |
|---|---|
| Público | `https://painel.cenarios.unb.br/cenarios/tbpe/` |
| Direto, por VPN | porta 8504 na VM dos painéis (`ssh cenarios-vm`) |
| Pasta na VM | `~/tbpe` |
| Dados | volume de `~/dashboard-sinan-pe/data` — a mesma extração do painel nacional; nada é copiado |

Substituiu o `tbpe` da geração anterior (Superset + `dados_dashboard/`) em
21/set/2026, no mesmo caminho e porta. O container antigo
(`dashboard-tb-pernambuco`, pasta `~/dashboard-tb-pernambuco`) ficou parado
na VM, não apagado — para voltar a ele: parar este e `docker compose up -d`
lá.

Deploy:

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
