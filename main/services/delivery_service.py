# main/services/delivery_service.py

from decimal import Decimal
from django.conf import settings

class DeliveryService:
    """Сервис расчета стоимости доставки"""
    
    DELIVERY_RATES = {
        'central': {
            'base': 300,
            'per_kg': 50,
            'min_order_free': 150000,  # Единый порог 150к
            'max_days': 3
        },
        'south': {
            'base': 400,
            'per_kg': 60,
            'min_order_free': 150000,
            'max_days': 4
        },
        'north_west': {
            'base': 450,
            'per_kg': 70,
            'min_order_free': 150000,
            'max_days': 5
        },
        'ural': {
            'base': 500,
            'per_kg': 80,
            'min_order_free': 150000,
            'max_days': 6
        },
        'siberia': {
            'base': 600,
            'per_kg': 100,
            'min_order_free': 150000,
            'max_days': 8
        },
        'far_east': {
            'base': 800,
            'per_kg': 150,
            'min_order_free': 150000,  # Теперь тоже 150к
            'max_days': 14
        }
    }
    
    CITY_TO_ZONE = {
        'центральный': ['москва', 'санкт-петербург', 'тверь', 'ярославль', 'владимир', 'кострома'],
        'южный': ['ростов', 'краснодар', 'сочи', 'волгоград', 'астрахань'],
        'северо-западный': ['мурманск', 'петрозаводск', 'архангельск', 'вологда'],
        'уральский': ['екатеринбург', 'челябинск', 'пермь', 'тюмень', 'уфа'],
        'сибирский': ['новосибирск', 'омск', 'красноярск', 'иркутск', 'барнаул'],
        'дальневосточный': ['владивосток', 'хабаровск', 'краснодар', 'якутск', 'петропавловск-камчатский']
    }
    
    @classmethod
    def detect_zone_by_city(cls, city_name):
        """Автоматическое определение зоны доставки по городу"""
        if not city_name:
            return 'central'
        
        city_lower = city_name.lower().strip()
        
        # Сопоставление городов с ключами из DELIVERY_RATES
        zone_mapping = {
            'central': ['москва', 'санкт-петербург', 'тверь', 'ярославль', 'кострома', 'иваново', 'владимир'],
            'south': ['ростов', 'краснодар', 'сочи', 'волгоград', 'астрахань'],
            'north_west': ['псков', 'новгород', 'калининград', 'мурманск'],
            'ural': ['екатеринбург', 'челябинск', 'пермь', 'тюмень'],
            'siberia': ['новосибирск', 'омск', 'красноярск', 'иркутск'],
            'far_east': ['владивосток', 'хабаровск', 'якутск']
        }
        
        for zone, cities in zone_mapping.items():
            for city in cities:
                if city in city_lower:
                    return zone
        
        return 'central'
    
    @classmethod
    def calculate_delivery_cost(cls, address, order_total, items_count, total_weight=0):
        """
        Расчет стоимости доставки
        
        Args:
            address: объект Address или dict с полями city/delivery_zone
            order_total: общая сумма заказа
            items_count: количество товаров
            total_weight: общий вес заказа в кг
        """
        if order_total >= Decimal('150000'):
            return Decimal('0')
        
        if hasattr(address, 'delivery_zone') and address.delivery_zone:
            zone = address.delivery_zone
        elif hasattr(address, 'city') and address.city:
            zone = cls.detect_zone_by_city(address.city)
        else:
            zone = 'central'
        
        rates = cls.DELIVERY_RATES.get(zone, cls.DELIVERY_RATES['central'])
        
        delivery_cost = Decimal(rates['base'])
        
        if total_weight > 0:
            weight_surcharge = Decimal(rates['per_kg']) * Decimal(total_weight)
            delivery_cost += weight_surcharge
        
        if items_count > 10:
            items_surcharge = (items_count - 10) * Decimal('50')
            delivery_cost += items_surcharge
        
        return delivery_cost.quantize(Decimal('0.01'))
    
    @classmethod
    def get_delivery_time(cls, address):
        """Получение срока доставки"""
        zone = 'central'
        
        if hasattr(address, 'delivery_zone') and address.delivery_zone:
            zone = address.delivery_zone
        elif hasattr(address, 'city') and address.city:
            zone = cls.detect_zone_by_city(address.city)
        
        rates = cls.DELIVERY_RATES.get(zone, cls.DELIVERY_RATES['central'])
        return f"{rates['max_days']} рабочих дней"
    
    @classmethod
    def get_available_couriers(cls, address):
        """Получение доступных служб доставки для адреса"""
        zone = 'central'
        
        if hasattr(address, 'delivery_zone') and address.delivery_zone:
            zone = address.delivery_zone
        elif hasattr(address, 'city') and address.city:
            zone = cls.detect_zone_by_city(address.city)
        
        couriers = {
            'central': ['СДЭК', 'Boxberry', 'Почта России', 'DPD'],
            'south': ['СДЭК', 'Почта России', 'DPD'],
            'north_west': ['СДЭК', 'Почта России'],
            'ural': ['СДЭК', 'Почта России'],
            'siberia': ['СДЭК', 'Почта России'],
            'far_east': ['Почта России']
        }
        
        return couriers.get(zone, ['Почта России'])
    
    @classmethod
    def get_delivery_zone_info(cls, city_name):
        """Получение информации о зоне доставки для города"""
        zone = cls.detect_zone_by_city(city_name)
        rates = cls.DELIVERY_RATES.get(zone, cls.DELIVERY_RATES['central'])
        
        return {
            'zone': zone,
            'base_cost': rates['base'],
            'delivery_time': f"{rates['max_days']} рабочих дней",
            'free_threshold': rates['min_order_free']
        }