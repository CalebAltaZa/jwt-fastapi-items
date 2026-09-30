"""Carga datos de demostración (Marvel) para tener contenido en el dashboard.

Uso (dentro del contenedor):
    docker compose exec items python -m app.seed --user caleb
"""

import argparse

from .db import get_conn, init_db, now_iso

MARVEL_ITEMS = [
    ("Avengers: Doomsday", "Películas", "https://picsum.photos/seed/doomsday/480/300",
     "La nueva saga de los Vengadores, dirigida por los hermanos Russo."),
    ("Spider-Man: Brand New Day", "Películas", "https://picsum.photos/seed/spidey/480/300",
     "Peter Parker vuelve con una nueva vida."),
    ("The Fantastic Four: First Steps", "Películas", "https://picsum.photos/seed/fantasticfour/480/300",
     "La Primera Liga se forma de nuevo."),
    ("What If...?", "Series", "https://picsum.photos/seed/whatif/480/300",
     "Qué pasaría si... el universo Marvel fuera diferente."),
    ("WandaVision", "Series", "https://picsum.photos/seed/wanda/480/300",
     "Scarlet Witch y su realidad alternativa."),
    ("Amazing Fantasy #15", "Cómics", "https://picsum.photos/seed/amazingfantasy/480/300",
     "La primera aparición de Spider-Man (1962)."),
    ("Civil War", "Cómics", "https://picsum.photos/seed/civilwar/480/300",
     "El Avengers original contra el Avengers original."),
    ("Doctor Doom", "Personajes", "https://picsum.photos/seed/doom/480/300",
     "Victor von Doom, el villano de Avengers: Doomsday."),
    ("Thanos", "Personajes", "https://picsum.photos/seed/thanos/480/300",
     "El Titán que parte el universo en dos."),
    ("Marvel's Spider-Man 2", "Videojuegos", "https://picsum.photos/seed/mssm2/480/300",
     "El juego de Insomniac con Peter y Miles."),
    ("Lego Marvel Super Heroes", "Videojuegos", "https://picsum.photos/seed/legomarvel/480/300",
     "Todos los héroes en formato Lego."),
    ("Mech Armor Collector", "Mercancía", "https://picsum.photos/seed/merc/480/300",
     "Coleccionable de la Stark Industries."),
]


def seed(username: str) -> int:
    init_db()
    with get_conn() as connection:
        existing = connection.execute(
            "SELECT COUNT(*) AS total FROM items WHERE username = ?", (username,)
        ).fetchone()["total"]
        if existing:
            print(f"[seed] {username} ya tiene {existing} items; no se insertó nada.")
            return 0
        created_at = now_iso()
        connection.executemany(
            "INSERT INTO items (username, name, category, image_url, note, favorite, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (username, name, category, image, note, 1 if index < 2 else 0, created_at)
                for index, (name, category, image, note) in enumerate(MARVEL_ITEMS)
            ],
        )
        total = len(MARVEL_ITEMS)
    print(f"[seed] {total} items Marvel cargados para {username}.")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    args = parser.parse_args()
    seed(args.user)
