
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class CommunityMarketplace:
    def __init__(self):
        self.marketplace_file = "marketplace.json"
        self.exchanges_file = "exchanges.json"
        self.marketplace_data = {}
        self.exchange_history = {}
        self.load_data()
    
    def load_data(self):
        """Cargar datos del marketplace"""
        try:
            if Path(self.marketplace_file).exists():
                with open(self.marketplace_file, 'r') as f:
                    data = json.load(f)
                    self.marketplace_data = data.get('listings', {})
                    logger.info(f"Loaded {len(self.marketplace_data)} marketplace listings")
            else:
                self.marketplace_data = {}
        except Exception as e:
            logger.error(f"Error loading marketplace data: {e}")
            self.marketplace_data = {}
        
        try:
            if Path(self.exchanges_file).exists():
                with open(self.exchanges_file, 'r') as f:
                    data = json.load(f)
                    self.exchange_history = data.get('exchanges', {})
                    logger.info(f"Loaded {len(self.exchange_history)} exchange records")
            else:
                self.exchange_history = {}
        except Exception as e:
            logger.error(f"Error loading exchange data: {e}")
            self.exchange_history = {}
    
    def save_data(self):
        """Guardar datos del marketplace"""
        try:
            data = {
                'listings': self.marketplace_data,
                'last_updated': datetime.now().isoformat(),
                'total_listings': len(self.marketplace_data)
            }
            with open(self.marketplace_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved marketplace data with {len(self.marketplace_data)} listings")
        except Exception as e:
            logger.error(f"Error saving marketplace data: {e}")
        
        try:
            data = {
                'exchanges': self.exchange_history,
                'last_updated': datetime.now().isoformat(),
                'total_exchanges': len(self.exchange_history)
            }
            with open(self.exchanges_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved exchange data with {len(self.exchange_history)} exchanges")
        except Exception as e:
            logger.error(f"Error saving exchange data: {e}")
    
    def create_listing(self, user_id: str, game_id: str, server_link: str, 
                      want_game_id: str, description: str = "", duration_hours: int = 24) -> str:
        """Crear un listing en el marketplace"""
        listing_id = f"listing_{int(time.time())}_{user_id}"
        
        listing = {
            'listing_id': listing_id,
            'user_id': user_id,
            'offer_game_id': game_id,
            'offer_server_link': server_link,
            'want_game_id': want_game_id,
            'description': description,
            'created_at': time.time(),
            'expires_at': time.time() + (duration_hours * 3600),
            'status': 'active',
            'interested_users': [],
            'views': 0
        }
        
        self.marketplace_data[listing_id] = listing
        self.save_data()
        
        logger.info(f"Created marketplace listing {listing_id} by user {user_id}")
        return listing_id
    
    def browse_listings(self, want_game_id: str = None, exclude_user: str = None) -> List[Dict]:
        """Navegar listings disponibles"""
        current_time = time.time()
        active_listings = []
        
        for listing_id, listing in self.marketplace_data.items():
            # Skip expired listings
            if listing['expires_at'] < current_time:
                continue
            
            # Skip own listings
            if exclude_user and listing['user_id'] == exclude_user:
                continue
            
            # Filter by wanted game
            if want_game_id and listing['offer_game_id'] != want_game_id:
                continue
            
            # Increment view count
            listing['views'] += 1
            
            active_listings.append(listing)
        
        # Sort by creation time (newest first)
        active_listings.sort(key=lambda x: x['created_at'], reverse=True)
        
        self.save_data()
        return active_listings
    
    def show_interest(self, listing_id: str, interested_user_id: str) -> bool:
        """Mostrar interés en un listing"""
        if listing_id not in self.marketplace_data:
            return False
        
        listing = self.marketplace_data[listing_id]
        
        # No permitir interés en propios listings
        if listing['user_id'] == interested_user_id:
            return False
        
        # Verificar que no esté expirado
        if listing['expires_at'] < time.time():
            return False
        
        # Agregar a lista de interesados si no está ya
        if interested_user_id not in listing['interested_users']:
            listing['interested_users'].append(interested_user_id)
            listing['last_interest'] = time.time()
            
            self.save_data()
            logger.info(f"User {interested_user_id} showed interest in listing {listing_id}")
            return True
        
        return False
    
    def accept_exchange(self, listing_id: str, selected_user_id: str, 
                       exchange_server_link: str) -> bool:
        """Aceptar un intercambio"""
        if listing_id not in self.marketplace_data:
            return False
        
        listing = self.marketplace_data[listing_id]
        
        # Verificar que el usuario interesado esté en la lista
        if selected_user_id not in listing['interested_users']:
            return False
        
        # Crear registro de intercambio
        exchange_id = f"exchange_{int(time.time())}_{listing['user_id']}_{selected_user_id}"
        
        exchange = {
            'exchange_id': exchange_id,
            'listing_id': listing_id,
            'offerer_user_id': listing['user_id'],
            'receiver_user_id': selected_user_id,
            'offerer_game_id': listing['offer_game_id'],
            'offerer_server_link': listing['offer_server_link'],
            'receiver_game_id': listing['want_game_id'],
            'receiver_server_link': exchange_server_link,
            'completed_at': time.time(),
            'rating_offerer': None,
            'rating_receiver': None
        }
        
        self.exchange_history[exchange_id] = exchange
        
        # Marcar listing como completado
        listing['status'] = 'completed'
        listing['completed_with'] = selected_user_id
        listing['completed_at'] = time.time()
        
        self.save_data()
        
        logger.info(f"Exchange {exchange_id} completed between {listing['user_id']} and {selected_user_id}")
        return True
    
    def rate_exchange(self, exchange_id: str, rater_user_id: str, rating: int) -> bool:
        """Calificar un intercambio"""
        if exchange_id not in self.exchange_history:
            return False
        
        exchange = self.exchange_history[exchange_id]
        
        # Verificar que el usuario puede calificar
        if rater_user_id == exchange['offerer_user_id']:
            exchange['rating_offerer'] = rating
        elif rater_user_id == exchange['receiver_user_id']:
            exchange['rating_receiver'] = rating
        else:
            return False
        
        self.save_data()
        return True
    
    def get_user_listings(self, user_id: str) -> List[Dict]:
        """Obtener listings de un usuario"""
        user_listings = []
        for listing in self.marketplace_data.values():
            if listing['user_id'] == user_id:
                user_listings.append(listing)
        
        user_listings.sort(key=lambda x: x['created_at'], reverse=True)
        return user_listings
    
    def get_user_exchanges(self, user_id: str) -> List[Dict]:
        """Obtener intercambios de un usuario"""
        user_exchanges = []
        for exchange in self.exchange_history.values():
            if (exchange['offerer_user_id'] == user_id or 
                exchange['receiver_user_id'] == user_id):
                user_exchanges.append(exchange)
        
        user_exchanges.sort(key=lambda x: x['completed_at'], reverse=True)
        return user_exchanges
    
    def get_user_rating(self, user_id: str) -> float:
        """Obtener rating promedio de un usuario"""
        ratings = []
        
        for exchange in self.exchange_history.values():
            if exchange['offerer_user_id'] == user_id and exchange['rating_receiver']:
                ratings.append(exchange['rating_receiver'])
            elif exchange['receiver_user_id'] == user_id and exchange['rating_offerer']:
                ratings.append(exchange['rating_offerer'])
        
        if not ratings:
            return 0.0
        
        return sum(ratings) / len(ratings)
    
    def cleanup_expired_listings(self):
        """Limpiar listings expirados"""
        current_time = time.time()
        expired_listings = []
        
        for listing_id, listing in self.marketplace_data.items():
            if listing['expires_at'] < current_time and listing['status'] == 'active':
                listing['status'] = 'expired'
                expired_listings.append(listing_id)
        
        if expired_listings:
            self.save_data()
            logger.info(f"Marked {len(expired_listings)} listings as expired")
        
        return len(expired_listings)
