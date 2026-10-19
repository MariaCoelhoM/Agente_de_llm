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
    """Popula os casos usados na demonstração (item 4.5 / case §2.8)."""
    clientes = [
        ("C001", "Marcos Silva", "Vila Nova"),   # caso simples
        ("C002", "Ana Souza", "Jardim Ipê"),     # caso de divergência
        ("C004", "Rita Mendes", "Vila Nova"),    # caso de falha física
        ("C005", "Pedro Alves", "Jardim Ipê"),   # caso: não deve agendar
        # C999 não existe de propósito — caso de registro inexistente
    ]
    modems = [
        ("C001", "AA:BB:01", "OFFLINE", -22.0, 0),
        ("C002", "AA:BB:02", "ONLINE", -18.0, 0),
        ("C004", "AA:BB:04", "OFFLINE", -30.0, 0),
        ("C005", "AA:BB:05", "OFFLINE", -19.0, 0),
    ]
    bairros = [("Vila Nova", 0), ("Jardim Ipê", 1)]  # Jardim Ipê em manutenção

    conn.executemany("INSERT OR IGNORE INTO clientes VALUES (?,?,?)", clientes)
    conn.executemany("INSERT OR IGNORE INTO modems VALUES (?,?,?,?,?)", modems)
    conn.executemany("INSERT OR IGNORE INTO bairros VALUES (?,?)", bairros)
    conn.commit()


def inicializar():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = conectar()
    criar_schema(conn)
    seed(conn)
    conn.close()


if __name__ == "__main__":
    inicializar()
    print(f"Banco criado em {DB_PATH}")