
import json
import time
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class RecommendationEngine:
    def __init__(self, scraper=None):
        self.scraper = scraper
        self.user_preferences = {}
        self.game_similarities = {}
        self.trend_data = {}
    
    def calculate_user_preferences(self, user_id: str) -> Dict[str, float]:
        """Calcular preferencias del usuario basado en su actividad"""
        if not self.scraper:
            return {}
        
        preferences = {
            'categories': defaultdict(float),
            'activity_times': defaultdict(int),
            'game_types': defaultdict(float),
            'server_count_preference': 0
        }
        
        # Analizar juegos del usuario
        user_games = self.scraper.links_by_user.get(user_id, {})
        total_servers = 0
        
        for game_id, game_data in user_games.items():
            category = game_data.get('category', 'other')
            server_count = len(game_data.get('links', []))
            
            # Peso por categoría
            preferences['categories'][category] += server_count
            total_servers += server_count
        
        # Normalizar preferencias de categoría
        if total_servers > 0:
            for category in preferences['categories']:
                preferences['categories'][category] /= total_servers
        
        # Analizar historial de uso
        user_history = self.scraper.usage_history.get(user_id, [])
        for entry in user_history:
            try:
                timestamp = datetime.fromisoformat(entry['timestamp'])
                hour = timestamp.hour
                
                # Preferencias de horario
                if 6 <= hour < 12:
                    preferences['activity_times']['morning'] += 1
                elif 12 <= hour < 18:
                    preferences['activity_times']['afternoon'] += 1
                elif 18 <= hour < 24:
                    preferences['activity_times']['evening'] += 1
                else:
                    preferences['activity_times']['night'] += 1
                
            except:
                continue
        
        # Preferencia de cantidad de servidores
        if user_games:
            avg_servers = total_servers / len(user_games)
            preferences['server_count_preference'] = avg_servers
        
        # Analizar favoritos
        user_favorites = self.scraper.user_favorites.get(user_id, [])
        for game_id in user_favorites:
            if game_id in user_games:
                category = user_games[game_id].get('category', 'other')
                preferences['categories'][category] += 0.5  # Bonus por favorito
        
        return dict(preferences)
    
    def get_similar_games(self, game_id: str, user_games: Dict) -> List[str]:
        """Encontrar juegos similares basado en categoría y patrones"""
        if game_id not in user_games:
            return []
        
        target_category = user_games[game_id].get('category', 'other')
        similar_games = []
        
        # Buscar en todos los usuarios para encontrar juegos similares
        for user_id, user_data in self.scraper.links_by_user.items():
            for other_game_id, other_game_data in user_data.items():
                if (other_game_id != game_id and 
                    other_game_data.get('category') == target_category):
                    similar_games.append(other_game_id)
        
        # Contar frecuencia y devolver los más comunes
        game_counter = Counter(similar_games)
        return [game_id for game_id, _ in game_counter.most_common(10)]
    
    def recommend_games_for_user(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Generar recomendaciones personalizadas para un usuario"""
        recommendations = []
        
        # Calcular preferencias del usuario
        preferences = self.calculate_user_preferences(user_id)
        
        if not preferences.get('categories'):
            # Usuario nuevo, recomendar juegos populares
            return self.get_trending_games(limit)
        
        # Obtener categorías preferidas
        preferred_categories = sorted(
            preferences['categories'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        user_games = self.scraper.links_by_user.get(user_id, {})
        
        # Buscar juegos recomendados por categoría
        for category, weight in preferred_categories[:3]:  # Top 3 categorías
            category_recommendations = self.get_games_by_category(
                category, exclude_user_games=user_games.keys(), limit=3
            )
            
            for game_rec in category_recommendations:
                game_rec['recommendation_reason'] = f"Te gusta la categoría {category}"
                game_rec['weight'] = weight
                recommendations.append(game_rec)
        
        # Agregar juegos similares a favoritos
        user_favorites = self.scraper.user_favorites.get(user_id, [])
        for fav_game_id in user_favorites[:2]:  # Top 2 favoritos
            if fav_game_id in user_games:
                similar_games = self.get_similar_games(fav_game_id, user_games)
                for similar_game_id in similar_games[:2]:
                    if similar_game_id not in user_games:
                        game_data = self.get_game_data(similar_game_id)
                        if game_data:
                            game_data['recommendation_reason'] = f"Similar a tu favorito {user_games[fav_game_id].get('game_name', 'juego')}"
                            game_data['weight'] = 0.8
                            recommendations.append(game_data)
        
        # Ordenar por peso y eliminar duplicados
        seen_games = set()
        unique_recommendations = []
        
        for rec in sorted(recommendations, key=lambda x: x.get('weight', 0), reverse=True):
            if rec['game_id'] not in seen_games:
                seen_games.add(rec['game_id'])
                unique_recommendations.append(rec)
        
        return unique_recommendations[:limit]
    
    def get_games_by_category(self, category: str, exclude_user_games: set = None, limit: int = 5) -> List[Dict]:
        """Obtener juegos por categoría"""
        if exclude_user_games is None:
            exclude_user_games = set()
        
        category_games = []
        
        # Buscar en todos los usuarios
        for user_id, user_games in self.scraper.links_by_user.items():
            for game_id, game_data in user_games.items():
                if (game_data.get('category') == category and 
                    game_id not in exclude_user_games):
                    
                    server_count = len(game_data.get('links', []))
                    if server_count > 0:  # Solo recomendar juegos con servidores
                        category_games.append({
                            'game_id': game_id,
                            'game_name': game_data.get('game_name', f'Game {game_id}'),
                            'category': category,
                            'server_count': server_count,
                            'popularity': self.calculate_game_popularity(game_id)
                        })
        
        # Eliminar duplicados y ordenar por popularidad
        unique_games = {}
        for game in category_games:
            game_id = game['game_id']
            if game_id not in unique_games:
                unique_games[game_id] = game
            else:
                # Sumar servidores de diferentes usuarios
                unique_games[game_id]['server_count'] += game['server_count']
        
        # Ordenar por popularidad y servidor count
        sorted_games = sorted(
            unique_games.values(),
            key=lambda x: (x['popularity'], x['server_count']),
            reverse=True
        )
        
        return sorted_games[:limit]
    
    def calculate_game_popularity(self, game_id: str) -> float:
        """Calcular popularidad de un juego"""
        popularity_score = 0
        
        # Contar en cuántos usuarios aparece
        user_count = 0
        total_servers = 0
        total_favorites = 0
        
        for user_id, user_games in self.scraper.links_by_user.items():
            if game_id in user_games:
                user_count += 1
                total_servers += len(user_games[game_id].get('links', []))
                
                # Bonus si está en favoritos
                if game_id in self.scraper.user_favorites.get(user_id, []):
                    total_favorites += 1
        
        # Calcular score
        popularity_score = user_count * 1.0 + total_servers * 0.1 + total_favorites * 2.0
        
        return popularity_score
    
    def get_trending_games(self, limit: int = 5) -> List[Dict]:
        """Obtener juegos en tendencia"""
        all_games = {}
        
        # Recopilar todos los juegos
        for user_id, user_games in self.scraper.links_by_user.items():
            for game_id, game_data in user_games.items():
                if game_id not in all_games:
                    all_games[game_id] = {
                        'game_id': game_id,
                        'game_name': game_data.get('game_name', f'Game {game_id}'),
                        'category': game_data.get('category', 'other'),
                        'server_count': 0,
                        'user_count': 0,
                        'popularity': 0
                    }
                
                all_games[game_id]['server_count'] += len(game_data.get('links', []))
                all_games[game_id]['user_count'] += 1
                all_games[game_id]['popularity'] = self.calculate_game_popularity(game_id)
        
        # Ordenar por popularidad
        trending = sorted(
            all_games.values(),
            key=lambda x: x['popularity'],
            reverse=True
        )
        
        # Agregar razón de recomendación
        for game in trending:
            game['recommendation_reason'] = "Juego popular en la comunidad"
            game['weight'] = game['popularity'] / 100  # Normalizar
        
        return trending[:limit]
    
    def get_game_data(self, game_id: str) -> Optional[Dict]:
        """Obtener datos de un juego específico"""
        for user_id, user_games in self.scraper.links_by_user.items():
            if game_id in user_games:
                game_data = user_games[game_id]
                return {
                    'game_id': game_id,
                    'game_name': game_data.get('game_name', f'Game {game_id}'),
                    'category': game_data.get('category', 'other'),
                    'server_count': len(game_data.get('links', [])),
                    'popularity': self.calculate_game_popularity(game_id)
                }
        return None
    
    def get_personalized_message(self, user_id: str) -> str:
        """Generar mensaje personalizado para el usuario"""
        preferences = self.calculate_user_preferences(user_id)
        
        if not preferences.get('categories'):
            return "¡Bienvenido! Explora diferentes categorías de juegos para obtener recomendaciones personalizadas."
        
        top_category = max(preferences['categories'].items(), key=lambda x: x[1])[0]
        
        messages = {
            'rpg': "¡Veo que te gustan los RPGs! Explora mundos épicos y aventuras.",
            'simulator': "¡Fan de los simuladores! Perfecto para relajarse y construir.",
            'action': "¡Amante de la acción! Prepárate para batallas intensas.",
            'horror': "¡Valiente! Los juegos de terror te esperan.",
            'social': "¡Sociable! Disfruta interactuando con otros jugadores.",
            'racing': "¡Velocidad! Domina las pistas a toda velocidad.",
            'puzzle': "¡Mente brillante! Los puzzles son tu especialidad.",
            'building': "¡Arquitecto creativo! Construye mundos increíbles.",
            'anime': "¡Otaku! Los mundos anime te están esperando."
        }
        
        return messages.get(top_category, "¡Sigue explorando y descubriendo nuevos juegos!")
