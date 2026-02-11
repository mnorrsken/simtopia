from __future__ import annotations

import math
import random
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "simtopia.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS planets (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                temperature TEXT NOT NULL,
                population INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goods (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                base_price INTEGER NOT NULL,
                category TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market (
                planet_id INTEGER NOT NULL,
                good_id INTEGER NOT NULL,
                price INTEGER NOT NULL,
                supply INTEGER NOT NULL,
                demand INTEGER NOT NULL,
                PRIMARY KEY (planet_id, good_id)
            );

            CREATE TABLE IF NOT EXISTS ship_types (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                cargo INTEGER NOT NULL,
                passenger INTEGER NOT NULL,
                warp_speed REAL NOT NULL,
                fuel INTEGER NOT NULL,
                cost INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS player (
                id INTEGER PRIMARY KEY,
                credits INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fleet (
                id INTEGER PRIMARY KEY,
                ship_type_id INTEGER NOT NULL,
                name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cargo (
                id INTEGER PRIMARY KEY,
                fleet_id INTEGER NOT NULL,
                good_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS routes (
                planet_a INTEGER NOT NULL,
                planet_b INTEGER NOT NULL,
                distance REAL NOT NULL,
                PRIMARY KEY (planet_a, planet_b)
            );
            """
        )
        conn.commit()


def seed_if_empty() -> None:
    with get_connection() as conn:
        planet_count = conn.execute("SELECT COUNT(*) AS c FROM planets").fetchone()["c"]
        rng = random.Random(42)
        if planet_count > 0:
            _seed_routes_if_missing(conn, rng)
            return

        goods = [
            ("Food", 30, "life"),
            ("Machinery", 120, "industry"),
            ("Minerals", 50, "raw"),
            ("Fuel", 80, "energy"),
            ("Fertilizer", 45, "agri"),
            ("Medicine", 140, "life"),
            ("Electronics", 160, "industry"),
            ("Luxury", 220, "trade"),
            ("Water", 20, "life"),
            ("Fusion Fuel", 180, "energy"),
        ]

        conn.executemany(
            "INSERT INTO goods (name, base_price, category) VALUES (?, ?, ?)",
            goods,
        )

        ship_types = [
            ("Courier", 20, 4, 9.5, 30, 400),
            ("Hauler", 120, 12, 6.0, 80, 1200),
            ("Clipper", 60, 40, 7.5, 60, 900),
            ("Bulk Freighter", 240, 20, 5.0, 140, 2200),
        ]
        conn.executemany(
            """
            INSERT INTO ship_types (name, cargo, passenger, warp_speed, fuel, cost)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ship_types,
        )

        conn.execute("INSERT INTO player (id, credits) VALUES (1, 1500)")
        conn.execute("INSERT INTO fleet (ship_type_id, name) VALUES (1, 'Starter')")

        planet_types = {
            "Earthlike": {
                "Food": -0.35,
                "Machinery": 0.2,
                "Fuel": 0.1,
                "Medicine": -0.1,
                "Electronics": 0.05,
                "Water": -0.3,
                "Fertilizer": 0.1,
            },
            "Gas Giant": {
                "Fuel": -0.4,
                "Fusion Fuel": -0.2,
                "Food": 0.35,
                "Water": 0.2,
            },
            "Lava": {
                "Fuel": -0.2,
                "Fusion Fuel": -0.25,
                "Machinery": 0.1,
                "Food": 0.3,
            },
            "Rock": {
                "Minerals": -0.35,
                "Machinery": 0.1,
                "Food": 0.25,
                "Fertilizer": -0.1,
            },
            "Barren": {
                "Minerals": -0.25,
                "Fuel": -0.1,
                "Food": 0.35,
            },
            "Ice": {
                "Water": -0.4,
                "Food": 0.2,
                "Fuel": 0.15,
            },
            "Ocean": {
                "Food": -0.25,
                "Water": -0.35,
                "Medicine": 0.1,
            },
            "Jungle": {
                "Food": -0.3,
                "Medicine": -0.2,
                "Machinery": 0.15,
            },
            "Desert": {
                "Minerals": -0.15,
                "Water": 0.35,
                "Food": 0.2,
            },
            "Tundra": {
                "Food": 0.1,
                "Fuel": 0.2,
                "Medicine": 0.15,
            },
            "Metallic": {
                "Minerals": -0.4,
                "Machinery": -0.1,
                "Food": 0.3,
            },
        }

        syllables = [
            "ar",
            "en",
            "ta",
            "ly",
            "zu",
            "on",
            "mir",
            "ver",
            "sol",
            "kal",
            "an",
            "tor",
            "shi",
            "pha",
            "zen",
            "ul",
            "cor",
            "pra",
            "is",
            "no",
            "qu",
        ]

        def make_name() -> str:
            parts = rng.randint(2, 3)
            name = "".join(rng.choice(syllables) for _ in range(parts))
            return name[:1].upper() + name[1:]

        planets = _generate_planets(rng, planet_types, make_name, count=60)

        conn.executemany(
            """
            INSERT INTO planets (name, type, x, y, temperature, population)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            planets,
        )

        goods_rows = conn.execute("SELECT id, name, base_price FROM goods").fetchall()
        planet_rows = conn.execute("SELECT id, type FROM planets").fetchall()

        market_rows: List[Tuple[int, int, int, int, int]] = []
        for planet in planet_rows:
            modifiers = planet_types.get(planet["type"], {})
            for good in goods_rows:
                base_price = good["base_price"]
                modifier = modifiers.get(good["name"], 0.0)
                noise = rng.uniform(-0.08, 0.08)
                price = base_price * (1 + modifier + noise)
                price = max(5, int(round(price)))
                supply = int(60 + 180 * max(0, -modifier) + rng.randint(0, 40))
                demand = int(60 + 180 * max(0, modifier) + rng.randint(0, 40))
                market_rows.append((planet["id"], good["id"], price, supply, demand))

        conn.executemany(
            """
            INSERT INTO market (planet_id, good_id, price, supply, demand)
            VALUES (?, ?, ?, ?, ?)
            """,
            market_rows,
        )
        _seed_routes_if_missing(conn, rng)
        conn.commit()


def _generate_planets(
    rng: random.Random,
    planet_types: Dict[str, Dict[str, float]],
    make_name: callable,
    count: int,
) -> List[Tuple[str, str, float, float, str, int]]:
    names = set()
    planets: List[Tuple[str, str, float, float, str, int]] = []
    for _ in range(count):
        name = make_name()
        while name in names:
            name = make_name()
        names.add(name)
        p_type = rng.choice(list(planet_types.keys()))
        x = rng.uniform(0, 1000)
        y = rng.uniform(0, 700)
        temp = rng.choice(["cold", "temperate", "hot"])
        population = rng.randint(1, 90) * 1_000_000
        planets.append((name, p_type, x, y, temp, population))
    return planets


def _seed_routes_if_missing(conn: sqlite3.Connection, rng: random.Random) -> None:
    route_count = conn.execute("SELECT COUNT(*) AS c FROM routes").fetchone()["c"]
    if route_count > 0:
        return

    planet_rows = conn.execute(
        "SELECT id, x, y FROM planets ORDER BY id"
    ).fetchall()
    if len(planet_rows) < 2:
        return

    points = [
        {"id": row["id"], "x": row["x"], "y": row["y"]}
        for row in planet_rows
    ]

    routes = _build_routes(points, rng)
    if not routes:
        return

    conn.executemany(
        "INSERT INTO routes (planet_a, planet_b, distance) VALUES (?, ?, ?)",
        routes,
    )
    conn.commit()


def _build_routes(
    points: List[Dict[str, float]],
    rng: random.Random,
    min_deg: int = 1,
    max_deg: int = 3,
    attempts: int = 12,
) -> Optional[List[Tuple[int, int, float]]]:
    n = len(points)
    if n < 2:
        return None

    all_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            distance = calculate_distance(
                (points[i]["x"], points[i]["y"]),
                (points[j]["x"], points[j]["y"]),
            )
            all_pairs.append((distance, i, j))
    all_pairs.sort(key=lambda item: item[0])

    def segments_cross(a: Dict[str, float], b: Dict[str, float], c: Dict[str, float], d: Dict[str, float]) -> bool:
        if (a is c) or (a is d) or (b is c) or (b is d):
            return False

        def ccw(p: Dict[str, float], q: Dict[str, float], r: Dict[str, float]) -> bool:
            return (r["y"] - p["y"]) * (q["x"] - p["x"]) > (q["y"] - p["y"]) * (r["x"] - p["x"])

        return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)

    for _ in range(attempts):
        targets = [rng.randint(min_deg, max_deg) for _ in range(n)]
        degrees = [0] * n
        edges: List[Tuple[int, int]] = []

        def can_add(i: int, j: int) -> bool:
            if degrees[i] >= max_deg or degrees[j] >= max_deg:
                return False
            a = points[i]
            b = points[j]
            for u, v in edges:
                if i in (u, v) or j in (u, v):
                    continue
                if segments_cross(a, b, points[u], points[v]):
                    return False
            return True

        for _, i, j in all_pairs:
            if degrees[i] >= targets[i] and degrees[j] >= targets[j]:
                continue
            if can_add(i, j):
                edges.append((i, j))
                degrees[i] += 1
                degrees[j] += 1

        for idx in range(n):
            if degrees[idx] >= min_deg:
                continue
            for _, i, j in all_pairs:
                if idx not in (i, j):
                    continue
                if can_add(i, j):
                    edges.append((i, j))
                    degrees[i] += 1
                    degrees[j] += 1
                    break

        if any(deg < min_deg for deg in degrees):
            continue

        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra = find(a)
            rb = find(b)
            if ra != rb:
                parent[rb] = ra

        for i, j in edges:
            union(i, j)

        def components() -> int:
            return len({find(i) for i in range(n)})

        if components() > 1:
            for _, i, j in all_pairs:
                if find(i) == find(j):
                    continue
                if can_add(i, j):
                    edges.append((i, j))
                    degrees[i] += 1
                    degrees[j] += 1
                    union(i, j)
                if components() == 1:
                    break

        if components() > 1:
            continue
        if any(deg < min_deg or deg > max_deg for deg in degrees):
            continue

        routes: List[Tuple[int, int, float]] = []
        for i, j in edges:
            a_id = int(points[i]["id"])
            b_id = int(points[j]["id"])
            if a_id > b_id:
                a_id, b_id = b_id, a_id
            distance = calculate_distance(
                (points[i]["x"], points[i]["y"]),
                (points[j]["x"], points[j]["y"]),
            )
            routes.append((a_id, b_id, round(distance, 2)))
        return routes

    return None


def calculate_distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])
