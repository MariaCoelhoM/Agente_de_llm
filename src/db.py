import hashlib
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "dados", "provedor.db")


def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def chave_visita(contrato: str, data: str) -> str:
    """Chave de idempotência derivada do conteúdo (enunciado §5.3 e §8.5):
    o mesmo contrato com a mesma data produz sempre a mesma chave."""
    return hashlib.sha256(f"{contrato}|{data}".encode("utf-8")).hexdigest()[:16]


def _migrar_visitas(conn):
    """Bancos criados antes da Parte 2 não têm a coluna `chave`. SQLite não
    adiciona coluna UNIQUE por ALTER TABLE, então a unicidade vai por índice."""
    colunas = [r["name"] for r in conn.execute("PRAGMA table_info(visitas)")]
    if "chave" not in colunas:
        conn.execute("ALTER TABLE visitas ADD COLUMN chave TEXT")
        vistas = set()
        for r in conn.execute("SELECT id, contrato, data FROM visitas").fetchall():
            chave = chave_visita(r["contrato"], r["data"])
            if chave in vistas:
                chave = f"{chave}-dup{r['id']}"
            vistas.add(chave)
            conn.execute("UPDATE visitas SET chave = ? WHERE id = ?", (chave, r["id"]))
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_visitas_chave ON visitas(chave)")
    conn.commit()


def criar_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            contrato TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            bairro TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS modems (
            contrato TEXT PRIMARY KEY REFERENCES clientes(contrato),
            mac TEXT NOT NULL,
            status TEXT NOT NULL,        -- ONLINE, OFFLINE
            sinal_dbm REAL NOT NULL,     -- sinal óptico; <= -27 é falha física
            reinicios_hoje INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS bairros (
            nome TEXT PRIMARY KEY,
            em_manutencao INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS canais (
            -- identidade vinda do canal (Parte 3, controle C1): no WhatsApp real,
            -- o número de telefone autenticado pelo app; aqui, simulado.
            telefone TEXT PRIMARY KEY,
            contrato TEXT NOT NULL REFERENCES clientes(contrato)
        );
        CREATE TABLE IF NOT EXISTS visitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contrato TEXT NOT NULL,
            data TEXT NOT NULL,
            status TEXT NOT NULL,
            chave TEXT NOT NULL UNIQUE   -- idempotência: derivada do conteúdo
        );
        """
    )
    conn.commit()
    _migrar_visitas(conn)


def seed(conn):
    """Popula os casos usados na demonstração e na suíte de avaliação
    (docs/case.md §8, evals/dataset.jsonl). Todos os dados são sintéticos."""
    clientes = [
        ("C001", "Marcos Silva", "Vila Nova"),    # caso simples: reinício resolve
        ("C002", "Ana Souza", "Jardim Ipê"),      # ONLINE + bairro em manutenção
        ("C003", "Luiza Prado", "Vila Nova"),     # divergência pura: ONLINE, bairro ok (devolutiva P1)
        ("C004", "Rita Mendes", "Vila Nova"),     # falha física (-30 dBm): precisa de visita
        ("C005", "Pedro Alves", "Jardim Ipê"),    # bairro em manutenção: não deve agendar
        ("C006", "Joana Reis", "Vila Nova"),      # borda: sinal exatamente -27,0 dBm (é falha física)
        ("C007", "Caio Nunes", "Vila Nova"),      # borda: -26,9 dBm (não é falha física)
        ("C008", "Rui Matos", "Bairro Novo"),     # bairro sem cadastro: bairro_nao_encontrado
        # C999 não existe de propósito — caso de registro inexistente
    ]
    modems = [
        ("C001", "AA:BB:01", "OFFLINE", -22.0, 0),
        ("C002", "AA:BB:02", "ONLINE", -18.0, 0),
        ("C003", "AA:BB:03", "ONLINE", -19.0, 0),
        ("C004", "AA:BB:04", "OFFLINE", -30.0, 0),
        ("C005", "AA:BB:05", "OFFLINE", -19.0, 0),
        ("C006", "AA:BB:06", "OFFLINE", -27.0, 0),
        ("C007", "AA:BB:07", "OFFLINE", -26.9, 0),
        ("C008", "AA:BB:08", "OFFLINE", -21.0, 0),
    ]
    bairros = [("Vila Nova", 0), ("Jardim Ipê", 1)]  # Jardim Ipê em manutenção; Bairro Novo sem cadastro
    canais = [  # telefones fictícios (faixa 90000-00xx)
        ("+5511900000001", "C001"), ("+5511900000002", "C002"), ("+5511900000003", "C003"),
        ("+5511900000004", "C004"), ("+5511900000005", "C005"), ("+5511900000006", "C006"),
        ("+5511900000007", "C007"), ("+5511900000008", "C008"),
    ]

    conn.executemany("INSERT OR IGNORE INTO clientes VALUES (?,?,?)", clientes)
    conn.executemany("INSERT OR IGNORE INTO modems VALUES (?,?,?,?,?)", modems)
    conn.executemany("INSERT OR IGNORE INTO bairros VALUES (?,?)", bairros)
    conn.executemany("INSERT OR IGNORE INTO canais VALUES (?,?)", canais)
    conn.commit()


def contrato_do_telefone(telefone: str):
    """Identidade vinda do canal: o contrato é o vinculado ao telefone que
    abriu a conversa. Devolve None para telefone sem cadastro."""
    conn = conectar()
    try:
        linha = conn.execute("SELECT contrato FROM canais WHERE telefone = ?",
                             (telefone.replace(" ", "").replace("-", ""),)).fetchone()
        return linha["contrato"] if linha else None
    finally:
        conn.close()


def resetar():
    """Apaga os bancos gerados (provedor, memória, checkpoints) e recria o
    provedor com o seed. Use antes de repetir uma demonstração: reiniciar a
    conexão muda o estado do modem."""
    from . import config
    for caminho in (DB_PATH, config.CAMINHO_MEMORIA, config.CAMINHO_CHECKPOINTS):
        for extra in ("", "-wal", "-shm"):
            if os.path.exists(caminho + extra):
                os.remove(caminho + extra)
    inicializar()


def inicializar():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = conectar()
    criar_schema(conn)
    seed(conn)
    conn.close()


if __name__ == "__main__":
    import sys
    resetar() if "--reset" in sys.argv else inicializar()
    print(f"Banco criado em {DB_PATH}")