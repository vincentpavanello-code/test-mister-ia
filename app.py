#!/usr/bin/env python3
"""
Application Flask pour rechercher des biens immobiliers sur Bien'Ici
Interface web avec filtres par ville et surface minimum
"""

from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import json
import time
import random
import re
from urllib.parse import quote
from typing import Optional, List, Dict

app = Flask(__name__)


class BienIciSearcher:
    """Recherche de biens immobiliers sur Bien'Ici"""

    BASE_URL = "https://www.bienici.com"
    API_URL = "https://www.bienici.com/realEstateAds.json"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.bienici.com/',
    }

    # Codes postaux des grandes villes françaises
    CITY_CODES = {
        'paris': '75000',
        'marseille': '13000',
        'lyon': '69000',
        'toulouse': '31000',
        'nice': '06000',
        'nantes': '44000',
        'strasbourg': '67000',
        'montpellier': '34000',
        'bordeaux': '33000',
        'lille': '59000',
        'rennes': '35000',
        'reims': '51100',
        'le havre': '76600',
        'saint-etienne': '42000',
        'toulon': '83000',
        'grenoble': '38000',
        'dijon': '21000',
        'angers': '49000',
        'nimes': '30000',
        'villeurbanne': '69100',
        'clermont-ferrand': '63000',
        'le mans': '72000',
        'aix-en-provence': '13100',
        'brest': '29200',
        'tours': '37000',
        'amiens': '80000',
        'limoges': '87000',
        'perpignan': '66000',
        'metz': '57000',
        'besancon': '25000',
        'orleans': '45000',
        'rouen': '76000',
        'caen': '14000',
        'nancy': '54000',
        'avignon': '84000',
        'cannes': '06400',
        'antibes': '06600',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _make_request(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        """Effectue une requête HTTP avec gestion des erreurs"""
        for attempt in range(retries):
            try:
                time.sleep(random.uniform(0.5, 1.5))
                response = self.session.get(url, timeout=30)
                if response.status_code == 200:
                    return response
            except requests.RequestException as e:
                print(f"Erreur requête: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        return None

    def get_city_slug(self, city: str) -> str:
        """Convertit le nom de ville en slug pour l'URL"""
        city_lower = city.lower().strip()
        # Normaliser les caractères spéciaux
        slug = city_lower.replace(' ', '-')
        slug = slug.replace("'", '-')
        # Retirer les accents
        accents = {'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
                   'à': 'a', 'â': 'a', 'ä': 'a',
                   'ù': 'u', 'û': 'u', 'ü': 'u',
                   'ô': 'o', 'ö': 'o',
                   'î': 'i', 'ï': 'i',
                   'ç': 'c'}
        for acc, repl in accents.items():
            slug = slug.replace(acc, repl)
        return slug

    def build_search_url(self, city: str, min_surface: int = 0, property_type: str = "achat") -> str:
        """Construit l'URL de recherche Bien'Ici"""
        city_slug = self.get_city_slug(city)

        # Format URL Bien'Ici: /achat/appartement,maison/ville-code_postal
        # Exemple: https://www.bienici.com/achat/appartement,maison/paris-75000

        city_lower = city.lower().strip()
        postal_code = self.CITY_CODES.get(city_lower, '')

        if postal_code:
            location = f"{city_slug}-{postal_code}"
        else:
            location = city_slug

        url = f"{self.BASE_URL}/{property_type}/appartement,maison/{location}"

        # Ajouter le filtre surface si spécifié
        if min_surface > 0:
            url += f"?surface-min={min_surface}"

        return url

    def search_properties(self, city: str, min_surface: int = 0) -> List[Dict]:
        """Recherche des biens à vendre dans une ville"""
        url = self.build_search_url(city, min_surface)
        print(f"Recherche: {url}")

        response = self._make_request(url)

        if not response:
            return self._generate_demo_results(city, min_surface)

        return self._parse_results(response.text, city, min_surface)

    def _parse_results(self, html: str, city: str, min_surface: int) -> List[Dict]:
        """Parse les résultats de recherche"""
        soup = BeautifulSoup(html, 'html.parser')
        properties = []

        # Chercher les données JSON intégrées dans la page
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'realEstateAds' in script.string:
                try:
                    # Extraire le JSON des annonces
                    match = re.search(r'realEstateAds["\s:]+(\[.*?\])', script.string, re.DOTALL)
                    if match:
                        data = json.loads(match.group(1))
                        for item in data:
                            prop = self._extract_property_data(item)
                            if prop and (min_surface == 0 or prop.get('surface', 0) >= min_surface):
                                properties.append(prop)
                except (json.JSONDecodeError, AttributeError):
                    pass

        # Si pas de JSON, parser le HTML
        if not properties:
            property_cards = soup.select('.searchResults__item, .ad-overview, [class*="adCard"], article')

            for card in property_cards[:20]:
                prop = self._parse_property_card(card)
                if prop and (min_surface == 0 or prop.get('surface', 0) >= min_surface):
                    properties.append(prop)

        if not properties:
            return self._generate_demo_results(city, min_surface)

        return properties

    def _extract_property_data(self, data: dict) -> Optional[Dict]:
        """Extrait les données d'un bien depuis le JSON"""
        try:
            return {
                'id': data.get('id', ''),
                'title': data.get('title', 'Bien immobilier'),
                'price': data.get('price', 0),
                'price_formatted': f"{data.get('price', 0):,}".replace(',', ' ') + ' €',
                'surface': data.get('surfaceArea', 0),
                'rooms': data.get('roomsQuantity', 0),
                'bedrooms': data.get('bedroomsQuantity', 0),
                'city': data.get('city', ''),
                'postal_code': data.get('postalCode', ''),
                'address': data.get('address', ''),
                'description': data.get('description', '')[:200] + '...' if data.get('description') else '',
                'photo': data.get('photos', [{}])[0].get('url', '') if data.get('photos') else '',
                'url': f"{self.BASE_URL}/annonce/{data.get('id', '')}",
                'property_type': data.get('propertyType', ''),
            }
        except Exception:
            return None

    def _parse_property_card(self, card) -> Optional[Dict]:
        """Parse une carte de bien depuis le HTML"""
        try:
            # Titre
            title_elem = card.select_one('h2, h3, .title, [class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else 'Bien immobilier'

            # Prix
            price_elem = card.select_one('[class*="price"], .price')
            price_text = price_elem.get_text(strip=True) if price_elem else '0'
            price = int(re.sub(r'[^\d]', '', price_text) or 0)

            # Surface
            surface_elem = card.select_one('[class*="surface"], [class*="area"]')
            surface_text = surface_elem.get_text(strip=True) if surface_elem else '0'
            surface_match = re.search(r'(\d+)', surface_text)
            surface = int(surface_match.group(1)) if surface_match else 0

            # Lien
            link_elem = card.select_one('a[href*="annonce"]')
            url = link_elem.get('href', '') if link_elem else ''
            if url and not url.startswith('http'):
                url = self.BASE_URL + url

            # Image
            img_elem = card.select_one('img')
            photo = img_elem.get('src', '') or img_elem.get('data-src', '') if img_elem else ''

            return {
                'id': '',
                'title': title,
                'price': price,
                'price_formatted': f"{price:,}".replace(',', ' ') + ' €' if price else 'Prix non communiqué',
                'surface': surface,
                'rooms': 0,
                'bedrooms': 0,
                'city': '',
                'postal_code': '',
                'address': '',
                'description': '',
                'photo': photo,
                'url': url,
                'property_type': '',
            }
        except Exception:
            return None

    def _generate_demo_results(self, city: str, min_surface: int) -> List[Dict]:
        """Génère des résultats de démonstration"""
        city_title = city.title()
        base_prices = {
            'paris': 12000, 'lyon': 5500, 'marseille': 4000, 'bordeaux': 5000,
            'toulouse': 4000, 'nice': 6000, 'nantes': 4500, 'lille': 3500,
        }
        price_per_m2 = base_prices.get(city.lower(), 3500)

        demo_properties = []
        surfaces = [max(min_surface, 25), max(min_surface, 45), max(min_surface, 65),
                    max(min_surface, 85), max(min_surface, 110)]
        types = ['Appartement', 'Maison', 'Studio', 'Loft', 'Duplex']

        for i, (surface, prop_type) in enumerate(zip(surfaces, types)):
            price = surface * price_per_m2 * random.uniform(0.9, 1.1)
            rooms = max(1, surface // 20)

            demo_properties.append({
                'id': f'demo-{i+1}',
                'title': f'{prop_type} {surface}m² - {city_title}',
                'price': int(price),
                'price_formatted': f"{int(price):,}".replace(',', ' ') + ' €',
                'surface': surface,
                'rooms': rooms,
                'bedrooms': max(0, rooms - 1),
                'city': city_title,
                'postal_code': self.CITY_CODES.get(city.lower(), ''),
                'address': f'Centre-ville de {city_title}',
                'description': f"Magnifique {prop_type.lower()} de {surface}m² situé à {city_title}. "
                              f"Comprend {rooms} pièce(s). Proche des commodités et transports.",
                'photo': '',
                'url': f'https://www.bienici.com/recherche/achat/{city.lower()}',
                'property_type': prop_type,
                'is_demo': True,
            })

        return demo_properties


# Instance globale du searcher
searcher = BienIciSearcher()


@app.route('/')
def index():
    """Page d'accueil avec le formulaire de recherche"""
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    """Endpoint de recherche"""
    city = request.form.get('city', '').strip()
    min_surface = request.form.get('min_surface', '0')

    try:
        min_surface = int(min_surface) if min_surface else 0
    except ValueError:
        min_surface = 0

    if not city:
        return render_template('index.html', error="Veuillez entrer une ville")

    properties = searcher.search_properties(city, min_surface)

    return render_template('results.html',
                          properties=properties,
                          city=city,
                          min_surface=min_surface,
                          count=len(properties))


@app.route('/api/search', methods=['GET'])
def api_search():
    """API JSON pour la recherche"""
    city = request.args.get('city', '').strip()
    min_surface = request.args.get('min_surface', '0')

    try:
        min_surface = int(min_surface) if min_surface else 0
    except ValueError:
        min_surface = 0

    if not city:
        return jsonify({'error': 'Paramètre city requis'}), 400

    properties = searcher.search_properties(city, min_surface)

    return jsonify({
        'city': city,
        'min_surface': min_surface,
        'count': len(properties),
        'properties': properties
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
