#!/usr/bin/env python3
"""
Interface CLI pour rechercher des biens immobiliers sur Bien'Ici
"""

import sys
sys.path.insert(0, '/home/user/test-mister-ia')

from app import BienIciSearcher


def main():
    print("\n" + "=" * 60)
    print("🏠  RECHERCHE IMMOBILIÈRE BIEN'ICI")
    print("=" * 60)

    # Demander la ville
    city = input("\n📍 Entrez une ville (ex: Paris, Lyon, Bordeaux): ").strip()
    if not city:
        city = "Paris"
        print(f"   → Ville par défaut: {city}")

    # Demander la surface minimum
    surface_input = input("📐 Surface minimum en m² (appuyez Entrée pour ignorer): ").strip()
    min_surface = int(surface_input) if surface_input.isdigit() else 0

    print(f"\n🔍 Recherche en cours pour {city.title()}", end="")
    if min_surface > 0:
        print(f" (surface min: {min_surface}m²)", end="")
    print("...\n")

    # Effectuer la recherche
    searcher = BienIciSearcher()
    properties = searcher.search_properties(city, min_surface)

    # Afficher les résultats
    print("\n" + "=" * 60)
    print(f"📊 {len(properties)} BIEN(S) TROUVÉ(S)")
    print("=" * 60)

    for i, prop in enumerate(properties, 1):
        print(f"\n{'─' * 60}")
        print(f"🏷️  BIEN #{i}")
        print(f"{'─' * 60}")
        print(f"   📌 {prop['title']}")
        print(f"   💰 Prix: {prop['price_formatted']}")
        if prop['surface'] > 0:
            print(f"   📐 Surface: {prop['surface']} m²")
        if prop['rooms'] > 0:
            print(f"   🚪 Pièces: {prop['rooms']}")
        if prop['bedrooms'] > 0:
            print(f"   🛏️  Chambres: {prop['bedrooms']}")
        if prop.get('address') or prop.get('city'):
            print(f"   📍 Lieu: {prop.get('address') or prop.get('city')} {prop.get('postal_code', '')}")
        if prop.get('description'):
            print(f"   📝 {prop['description'][:100]}...")
        print(f"   🔗 {prop['url']}")

        if prop.get('is_demo'):
            print(f"   ⚡ (Données de démonstration)")

    print(f"\n{'=' * 60}")
    print("✅ Recherche terminée!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
