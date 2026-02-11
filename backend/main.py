from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .db import calculate_distance, get_connection, init_db, seed_if_empty

app = FastAPI(title="Simtopia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed_if_empty()


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/planets")
def list_planets() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, type, x, y, temperature, population FROM planets"
        ).fetchall()
        return [dict(row) for row in rows]


@app.get("/api/planets/{planet_id}/market")
def planet_market(planet_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        planet = conn.execute(
            "SELECT id FROM planets WHERE id = ?", (planet_id,)
        ).fetchone()
        if not planet:
            raise HTTPException(status_code=404, detail="Planet not found")

        rows = conn.execute(
            """
            SELECT goods.id AS good_id, goods.name, goods.category,
                   market.price, market.supply, market.demand
            FROM market
            JOIN goods ON goods.id = market.good_id
            WHERE market.planet_id = ?
            ORDER BY goods.name
            """,
            (planet_id,),
        ).fetchall()
        return [dict(row) for row in rows]


@app.get("/api/goods")
def list_goods() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, base_price, category FROM goods ORDER BY name"
        ).fetchall()
        return [dict(row) for row in rows]


@app.get("/api/ships")
def list_ships() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, cargo, passenger, warp_speed, fuel, cost
            FROM ship_types
            ORDER BY cost
            """
        ).fetchall()
        return [dict(row) for row in rows]


@app.get("/api/player")
def get_player() -> Dict[str, Any]:
    with get_connection() as conn:
        player = conn.execute("SELECT credits FROM player WHERE id = 1").fetchone()
        fleet = conn.execute(
            """
            SELECT fleet.id, fleet.name, ship_types.name AS ship_type,
                   ship_types.cargo, ship_types.passenger, ship_types.warp_speed
            FROM fleet
            JOIN ship_types ON ship_types.id = fleet.ship_type_id
            ORDER BY fleet.id
            """
        ).fetchall()
        return {"credits": player["credits"], "fleet": [dict(row) for row in fleet]}


@app.post("/api/buy_ship")
def buy_ship(payload: Dict[str, Any]) -> Dict[str, Any]:
    ship_type_id = int(payload.get("ship_type_id", 0))
    name = payload.get("name") or "New Ship"

    with get_connection() as conn:
        ship = conn.execute(
            "SELECT cost FROM ship_types WHERE id = ?", (ship_type_id,)
        ).fetchone()
        if not ship:
            raise HTTPException(status_code=404, detail="Ship type not found")

        player = conn.execute("SELECT credits FROM player WHERE id = 1").fetchone()
        if player["credits"] < ship["cost"]:
            raise HTTPException(status_code=400, detail="Not enough credits")

        conn.execute(
            "INSERT INTO fleet (ship_type_id, name) VALUES (?, ?)",
            (ship_type_id, name),
        )
        conn.execute(
            "UPDATE player SET credits = credits - ? WHERE id = 1",
            (ship["cost"],),
        )
        conn.commit()

    return get_player()


@app.get("/api/routes")
def best_routes(planet_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        source = conn.execute(
            "SELECT id, name, x, y FROM planets WHERE id = ?", (planet_id,)
        ).fetchone()
        if not source:
            raise HTTPException(status_code=404, detail="Planet not found")

        source_prices = conn.execute(
            """
            SELECT market.good_id, goods.name, market.price
            FROM market
            JOIN goods ON goods.id = market.good_id
            WHERE market.planet_id = ?
            """,
            (planet_id,),
        ).fetchall()

        source_price_map = {row["good_id"]: row for row in source_prices}

        targets = conn.execute(
            "SELECT id, name, x, y, type FROM planets WHERE id != ?", (planet_id,)
        ).fetchall()

        opportunities: List[Dict[str, Any]] = []
        for target in targets:
            distance = calculate_distance((source["x"], source["y"]), (target["x"], target["y"]))
            target_prices = conn.execute(
                """
                SELECT market.good_id, market.price
                FROM market
                WHERE market.planet_id = ?
                """,
                (target["id"],),
            ).fetchall()
            for t_row in target_prices:
                s_row = source_price_map.get(t_row["good_id"])
                if not s_row:
                    continue
                profit = t_row["price"] - s_row["price"]
                if profit <= 0:
                    continue
                opportunities.append(
                    {
                        "from_id": source["id"],
                        "from_name": source["name"],
                        "to_id": target["id"],
                        "to_name": target["name"],
                        "to_type": target["type"],
                        "good_id": s_row["good_id"],
                        "good": s_row["name"],
                        "profit_per_unit": profit,
                        "distance": round(distance, 2),
                        "profit_per_distance": round(profit / max(distance, 1), 2),
                    }
                )

        opportunities.sort(
            key=lambda item: (item["profit_per_distance"], item["profit_per_unit"]),
            reverse=True,
        )
        return opportunities[: max(1, min(limit, 30))]


@app.get("/api/lanes")
def list_lanes() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.planet_a, r.planet_b,
                   pa.name AS a_name, pa.x AS ax, pa.y AS ay,
                   pb.name AS b_name, pb.x AS bx, pb.y AS by,
                   r.distance
            FROM routes r
            JOIN planets pa ON pa.id = r.planet_a
            JOIN planets pb ON pb.id = r.planet_b
            """
        ).fetchall()
        return [dict(row) for row in rows]


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")
