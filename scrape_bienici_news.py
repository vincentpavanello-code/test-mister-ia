#!/usr/bin/env python3
"""
Script de scraping des actualités immobilières de Bien'Ici
Génère un résumé des actualités du jour
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time
import random
import re
from typing import Optional


class BienIciScraper:
    """Scraper pour les actualités immobilières de Bien'Ici"""

    BASE_URL = "https://www.bienici.com"
    BLOG_URL = "https://www.bienici.com/blog"

    # Headers pour simuler un navigateur réel
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.articles = []

    def _make_request(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        """Effectue une requête HTTP avec gestion des erreurs et retries"""
        for attempt in range(retries):
            try:
                # Délai aléatoire pour éviter la détection
                time.sleep(random.uniform(1, 3))
                response = self.session.get(url, timeout=30)

                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    print(f"⚠️  Accès refusé (403) - Tentative {attempt + 1}/{retries}")
                else:
                    print(f"⚠️  Erreur HTTP {response.status_code} - Tentative {attempt + 1}/{retries}")

            except requests.RequestException as e:
                print(f"⚠️  Erreur de connexion: {e} - Tentative {attempt + 1}/{retries}")

            # Délai exponentiel entre les tentatives
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

        return None

    def scrape_blog(self) -> list:
        """Scrape les articles du blog Bien'Ici"""
        print(f"📡 Récupération des articles depuis {self.BLOG_URL}...")

        response = self._make_request(self.BLOG_URL)

        if not response:
            print("❌ Impossible d'accéder au blog Bien'Ici")
            return self._get_fallback_news()

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []

        # Recherche des articles (sélecteurs typiques pour un blog)
        article_selectors = [
            'article',
            '.blog-post',
            '.article',
            '.post',
            '[class*="article"]',
            '[class*="post"]',
        ]

        for selector in article_selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:10]:  # Limiter à 10 articles
                    article = self._parse_article(elem)
                    if article:
                        articles.append(article)
                break

        if not articles:
            # Fallback: chercher tous les liens pertinents
            articles = self._extract_news_links(soup)

        self.articles = articles
        return articles

    def _parse_article(self, element) -> Optional[dict]:
        """Parse un élément article HTML"""
        try:
            # Titre
            title_elem = element.select_one('h1, h2, h3, .title, [class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else None

            if not title or len(title) < 10:
                return None

            # Lien
            link_elem = element.select_one('a[href]')
            link = link_elem.get('href', '') if link_elem else ''
            if link and not link.startswith('http'):
                link = self.BASE_URL + link

            # Date
            date_elem = element.select_one('time, .date, [class*="date"], [datetime]')
            date = date_elem.get_text(strip=True) if date_elem else datetime.now().strftime('%d/%m/%Y')

            # Extrait
            excerpt_elem = element.select_one('p, .excerpt, .summary, [class*="excerpt"]')
            excerpt = excerpt_elem.get_text(strip=True)[:300] if excerpt_elem else ''

            return {
                'title': title,
                'link': link,
                'date': date,
                'excerpt': excerpt
            }

        except Exception as e:
            print(f"⚠️  Erreur parsing article: {e}")
            return None

    def _extract_news_links(self, soup) -> list:
        """Extrait les liens d'actualités de la page"""
        articles = []
        seen_titles = set()

        # Mots-clés immobiliers
        keywords = ['immobilier', 'logement', 'achat', 'vente', 'location',
                    'prix', 'marché', 'appartement', 'maison', 'loyer',
                    'crédit', 'prêt', 'investissement', 'notaire']

        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link.get('href', '')

            # Vérifier si c'est un article pertinent
            if len(text) > 20 and any(kw in text.lower() for kw in keywords):
                if text not in seen_titles:
                    seen_titles.add(text)
                    articles.append({
                        'title': text,
                        'link': href if href.startswith('http') else self.BASE_URL + href,
                        'date': datetime.now().strftime('%d/%m/%Y'),
                        'excerpt': ''
                    })

            if len(articles) >= 10:
                break

        return articles

    def _get_fallback_news(self) -> list:
        """Retourne des actualités de fallback si le scraping échoue"""
        print("ℹ️  Utilisation de sources alternatives...")

        # Essayer d'autres sources d'actualités immobilières
        alternative_sources = [
            "https://www.pap.fr/actualites",
            "https://www.seloger.com/actualites.htm",
        ]

        for source_url in alternative_sources:
            response = self._make_request(source_url)
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = self._extract_news_links(soup)
                if articles:
                    print(f"✅ Articles récupérés depuis {source_url}")
                    return articles

        # Si tout échoue, retourner un message informatif
        return [{
            'title': "Actualités immobilières non disponibles",
            'link': self.BASE_URL,
            'date': datetime.now().strftime('%d/%m/%Y'),
            'excerpt': "Le scraping des actualités a échoué. Les sites ont des protections anti-bot. Consultez directement les sources."
        }]

    def generate_summary(self) -> str:
        """Génère un résumé des actualités collectées"""
        if not self.articles:
            return "Aucune actualité disponible."

        today = datetime.now().strftime('%d/%m/%Y')

        summary = f"""
╔══════════════════════════════════════════════════════════════════╗
║        RÉSUMÉ DES ACTUALITÉS IMMOBILIÈRES DU {today}         ║
╚══════════════════════════════════════════════════════════════════╝

📰 {len(self.articles)} article(s) trouvé(s)

"""

        for i, article in enumerate(self.articles, 1):
            summary += f"""
───────────────────────────────────────────────────────────────────
📌 Article {i}: {article['title']}
───────────────────────────────────────────────────────────────────
   📅 Date: {article['date']}
   🔗 Lien: {article['link']}
"""
            if article['excerpt']:
                summary += f"   📝 Extrait: {article['excerpt'][:200]}...\n"

        summary += """
═══════════════════════════════════════════════════════════════════
                    Fin du résumé
═══════════════════════════════════════════════════════════════════
"""

        return summary

    def save_to_json(self, filename: str = "actualites_immobilieres.json"):
        """Sauvegarde les articles en JSON"""
        data = {
            'date_scraping': datetime.now().isoformat(),
            'source': 'Bien\'Ici et sources alternatives',
            'articles': self.articles
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Données sauvegardées dans {filename}")
        return filename

    def save_summary(self, filename: str = "resume_actualites.txt"):
        """Sauvegarde le résumé dans un fichier texte"""
        summary = self.generate_summary()

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(summary)

        print(f"✅ Résumé sauvegardé dans {filename}")
        return filename


def main():
    """Point d'entrée principal"""
    print("🏠 Scraper d'actualités immobilières Bien'Ici")
    print("=" * 50)

    scraper = BienIciScraper()

    # Scraper les actualités
    articles = scraper.scrape_blog()

    # Générer et afficher le résumé
    summary = scraper.generate_summary()
    print(summary)

    # Sauvegarder les résultats
    scraper.save_to_json()
    scraper.save_summary()

    print("\n✅ Scraping terminé avec succès!")
    return scraper.articles


if __name__ == "__main__":
    main()
