"""Carga datos de demostración (Marvel) para tener contenido en el dashboard.

Uso (dentro del contenedor):
    docker compose exec items python -m app.seed --user caleb
"""

import argparse

from .db import get_conn, init_db, now_iso

# Las imágenes son SVG locales que sirve el frontend (/posters/*.svg), así el
# dashboard funciona sin internet. El frontend cae a /posters/fallback.svg si
# una URL falla.
MARVEL_ITEMS = [
    ("Avengers: Doomsday", "Películas", "/posters/doomsday.svg",
     "La nueva saga de los Vengadores, dirigida por los hermanos Russo."),
    ("Spider-Man: Brand New Day", "Películas", "/posters/spidey.svg",
     "Peter Parker vuelve con una nueva vida."),
    ("The Fantastic Four: First Steps", "Películas", "/posters/fantastic-four.svg",
     "La Primera Liga se forma de nuevo."),
    ("Black Panther: Wakanda Forever", "Películas", "/posters/wakanda.svg",
     "Wakanda Forever: el legado de T'Challa."),
    ("What If...?", "Series", "/posters/whatif.svg",
     "Qué pasaría si... el universo Marvel fuera diferente."),
    ("WandaVision", "Series", "/posters/wanda.svg",
     "Scarlet Witch y su realidad alternativa."),
    ("Amazing Fantasy #15", "Cómics", "/posters/amazing-fantasy.svg",
     "La primera aparición de Spider-Man (1962)."),
    ("Civil War", "Cómics", "/posters/civil-war.svg",
     "Los Vengadores originales contra sí mismos."),
    ("Doctor Doom", "Personajes", "/posters/doom.svg",
     "Victor von Doom, el villano de Avengers: Doomsday."),
    ("Thanos", "Personajes", "/posters/thanos.svg",
     "El Titán que parte el universo en dos."),
    ("Marvel's Spider-Man 2", "Videojuegos", "/posters/mssm2.svg",
     "El juego de Insomniac con Peter y Miles."),
    ("Lego Marvel Super Heroes", "Videojuegos", "/posters/lego.svg",
     "Todos los héroes en formato Lego."),
    ("Mech Armor Collector", "Mercancía", "/posters/mech.svg",
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
