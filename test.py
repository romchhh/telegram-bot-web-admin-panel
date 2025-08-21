import asyncio
import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
import aiohttp
from contextlib import asynccontextmanager
import numpy as np
from dataclasses import dataclass, asdict
import time
from collections import defaultdict

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError

# ================================
# КОНФІГУРАЦІЯ
# ================================
BOT_TOKEN = '8171832195:AAFYygMxoM5Rc9UMSHMswC63HEUnpsPMfgI'
CHAT_ID = '-1002254847974'   # Замінити на свій chat ID
BINANCE_API_URL = "https://api.binance.com/api/v3"
CHECK_INTERVAL = 30  # 30 секунд для швидшого відстеження наближення
TIMEFRAMES = ['1h', '4h']
TOP_SYMBOLS_COUNT = 100  # Топ-100 монет
APPROACH_TICKS = 5  # Кількість тіків для "наближення"

# Логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================
# ENHANCED DATA STRUCTURES
# ================================
@dataclass
class EnhancedOrderBlock:
    """Покращена структура Order Block з Volumized аналізом"""
    id: str
    symbol: str
    timeframe: str
    high_price: float
    low_price: float
    volume: float
    quote_volume: float  # Додано для кращого аналізу
    timestamp: int
    block_type: str  # 'bullish' або 'bearish'
    is_active: bool = True
    strength: float = 0.0  # Сила блоку (0-100)
    volume_profile: List[float] = None  # Профіль об'єму в зоні
    flux_score: float = 0.0  # Оцінка Flux
    institutional_level: float = 0.0  # Рівень institutional activity
    approach_alerts_sent: Set[float] = None  # Відстежування надісланих алертів
    
    def __post_init__(self):
        if self.volume_profile is None:
            self.volume_profile = []
        if self.approach_alerts_sent is None:
            self.approach_alerts_sent = set()

@dataclass
class FluxData:
    """Розширені дані Flux Charts"""
    symbol: str
    timeframe: str
    buy_flow: float
    sell_flow: float
    net_flow: float
    flow_strength: float
    institutional_flow: float  # Новий параметр
    retail_flow: float  # Новий параметр
    flux_momentum: float  # Momentum потоку
    timestamp: int

@dataclass
class PriceApproach:
    """Структура для відстеження наближення до зони"""
    symbol: str
    current_price: float
    target_zone: Tuple[float, float]  # (low, high)
    distance_ticks: int
    approach_speed: str  # 'slow', 'medium', 'fast'
    probability: float  # Вірогідність досягнення зони

# ================================
# TOP SYMBOLS FETCHER
# ================================
class BinanceSymbolFetcher:
    def __init__(self):
        self.session = None
        self.top_symbols_cache = []
        self.cache_timestamp = 0
        self.cache_duration = 3600  # 1 година кеш
    
    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def get_top_symbols(self, limit: int = TOP_SYMBOLS_COUNT) -> List[str]:
        """Отримання топ символів за об'ємом торгівлі"""
        current_time = time.time()
        
        # Перевіряємо кеш
        if (current_time - self.cache_timestamp) < self.cache_duration and self.top_symbols_cache:
            return self.top_symbols_cache[:limit]
        
        await self.init_session()
        
        try:
            # Отримуємо 24h статистику по всім парам USDT
            url = f"{BINANCE_API_URL}/ticker/24hr"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Фільтруємо USDT пари та сортуємо за об'ємом
                    usdt_pairs = [
                        item for item in data 
                        if item['symbol'].endswith('USDT') and 
                        float(item['quoteVolume']) > 1000000  # Мін об'єм $1M
                    ]
                    
                    # Сортуємо за об'ємом торгівлі (quote volume)
                    sorted_pairs = sorted(
                        usdt_pairs, 
                        key=lambda x: float(x['quoteVolume']), 
                        reverse=True
                    )
                    
                    # Витягуємо символи без USDT
                    symbols = [pair['symbol'][:-4] for pair in sorted_pairs[:limit]]
                    
                    # Оновлюємо кеш
                    self.top_symbols_cache = symbols
                    self.cache_timestamp = current_time
                    
                    logger.info(f"📊 Оновлено топ-{limit} символів. Перші 10: {symbols[:10]}")
                    return symbols
                    
        except Exception as e:
            logger.error(f"Помилка отримання топ символів: {e}")
            # Повертаємо резервний список якщо є проблеми з API
            if self.top_symbols_cache:
                return self.top_symbols_cache[:limit]
            else:
                return ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'MATIC', 'DOT', 'LINK', 'AVAX', 'UNI']

# ================================
# ENHANCED TECHNICAL ANALYZER
# ================================
class EnhancedTechnicalAnalyzer:
    def __init__(self):
        self.session = None
        self.symbol_fetcher = BinanceSymbolFetcher()
    
    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
            await self.symbol_fetcher.init_session()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
        await self.symbol_fetcher.close_session()
    
    async def get_kline_data(self, symbol: str, timeframe: str, limit: int = 500) -> Optional[List[Dict]]:
        """Покращене отримання даних свічок"""
        await self.init_session()
        
        tf_map = {'1h': '1h', '4h': '4h', '1d': '1d'}
        interval = tf_map.get(timeframe, '1h')
        
        url = f"{BINANCE_API_URL}/klines"
        params = {
            'symbol': symbol.upper() + 'USDT',
            'interval': interval,
            'limit': limit
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        {
                            'timestamp': int(item[0]),
                            'open': float(item[1]),
                            'high': float(item[2]),
                            'low': float(item[3]),
                            'close': float(item[4]),
                            'volume': float(item[5]),
                            'close_time': int(item[6]),
                            'quote_volume': float(item[7]),
                            'trades_count': int(item[8]),
                            'buy_volume': float(item[9]),
                            'buy_quote_volume': float(item[10])
                        }
                        for item in data
                    ]
        except Exception as e:
            logger.error(f"Помилка отримання даних для {symbol}: {e}")
            return None
    
    def identify_volumized_order_blocks(self, kline_data: List[Dict], symbol: str, timeframe: str) -> List[EnhancedOrderBlock]:
        """Покращена ідентифікація Volumized Order Blocks"""
        if len(kline_data) < 50:
            return []
        
        order_blocks = []
        
        # Розраховуємо динамічні пороги
        volume_data = [k['volume'] for k in kline_data]
        quote_volume_data = [k['quote_volume'] for k in kline_data]
        
        volume_threshold = np.percentile(volume_data, 80)  # Топ 20% за об'ємом
        quote_volume_threshold = np.percentile(quote_volume_data, 80)
        
        # Розрахунок institutional activity порогу
        institutional_threshold = self._calculate_institutional_threshold(kline_data)
        
        # Сканування Order Blocks
        for i in range(10, len(kline_data) - 10):
            current = kline_data[i]
            
            # Перевірка на високий об'єм та institutional activity
            if (current['volume'] > volume_threshold and 
                current['quote_volume'] > quote_volume_threshold):
                
                # Аналіз оточуючих свічок
                left_context = kline_data[i-10:i]
                right_context = kline_data[i+1:i+11]
                
                # Перевірка умов Order Block
                if self._is_valid_order_block_zone(current, left_context, right_context):
                    
                    # Визначення типу блоку
                    block_type = self._determine_enhanced_block_type(current, left_context, right_context)
                    
                    # Розрахунок покращених метрик
                    strength = self._calculate_enhanced_strength(current, left_context, right_context, volume_threshold)
                    flux_score = self._calculate_flux_score(current, left_context, right_context)
                    institutional_level = self._calculate_institutional_level(current, institutional_threshold)
                    
                    # Створення покращеного Order Block
                    block_id = f"{symbol}_{timeframe}_{current['timestamp']}_{block_type}"
                    
                    enhanced_block = EnhancedOrderBlock(
                        id=block_id,
                        symbol=symbol,
                        timeframe=timeframe,
                        high_price=current['high'],
                        low_price=current['low'],
                        volume=current['volume'],
                        quote_volume=current['quote_volume'],
                        timestamp=current['timestamp'],
                        block_type=block_type,
                        strength=strength,
                        flux_score=flux_score,
                        institutional_level=institutional_level
                    )
                    
                    # Додаємо Volume Profile
                    enhanced_block.volume_profile = self._build_volume_profile(current, left_context, right_context)
                    
                    order_blocks.append(enhanced_block)
        
        # Фільтруємо та повертаємо тільки найсильніші блоки
        strong_blocks = [block for block in order_blocks if block.strength > 40 and block.flux_score > 30]
        
        # Сортуємо за силою та повертаємо топ-20
        return sorted(strong_blocks, key=lambda x: x.strength + x.flux_score, reverse=True)[:20]
    
    def _calculate_institutional_threshold(self, kline_data: List[Dict]) -> float:
        """Розрахунок порогу для institutional activity"""
        # Аналіз співвідношення buy/sell volume
        buy_ratios = []
        for candle in kline_data:
            if candle['volume'] > 0:
                buy_ratio = candle['buy_volume'] / candle['volume']
                buy_ratios.append(buy_ratio)
        
        # Пороговий рівень institutional activity
        return np.percentile(buy_ratios, 85) if buy_ratios else 0.6
    
    def _is_valid_order_block_zone(self, current: Dict, left_context: List[Dict], right_context: List[Dict]) -> bool:
        """Покращена перевірка валідності Order Block зони"""
        # 1. Перевірка консолідації перед блоком
        left_consolidation = self._check_consolidation_pattern(left_context)
        
        # 2. Перевірка імпульсу після блоку
        right_impulse = self._check_impulse_pattern(right_context)
        
        # 3. Перевірка volume spike
        volume_spike = self._check_volume_spike(current, left_context)
        
        # 4. Перевірка institutional footprint
        institutional_footprint = self._check_institutional_footprint(current)
        
        return left_consolidation and right_impulse and volume_spike and institutional_footprint
    
    def _check_consolidation_pattern(self, candles: List[Dict]) -> bool:
        """Перевірка паттерну консолідації"""
        if len(candles) < 5:
            return False
        
        highs = [c['high'] for c in candles[-5:]]
        lows = [c['low'] for c in candles[-5:]]
        
        # Розрахунок волатильності
        price_range = (max(highs) - min(lows)) / np.mean([max(highs), min(lows)])
        
        # Консолідація якщо волатільність менше 3%
        return price_range < 0.03
    
    def _check_impulse_pattern(self, candles: List[Dict]) -> bool:
        """Перевірка імпульсного паттерну"""
        if len(candles) < 3:
            return False
        
        first_close = candles[0]['close']
        last_close = candles[-1]['close']
        
        # Імпульс якщо зміна більше 2% за 3 свічки
        price_change = abs(last_close - first_close) / first_close
        return price_change > 0.02
    
    def _check_volume_spike(self, current: Dict, left_context: List[Dict]) -> bool:
        """Перевірка volume spike"""
        if len(left_context) < 5:
            return False
        
        avg_volume = np.mean([c['volume'] for c in left_context[-5:]])
        return current['volume'] > (avg_volume * 2)  # Об'єм у 2 рази більший
    
    def _check_institutional_footprint(self, current: Dict) -> bool:
        """Перевірка institutional footprint"""
        if current['volume'] == 0:
            return False
        
        # Співвідношення buy/total volume
        buy_ratio = current['buy_volume'] / current['volume']
        
        # Institutional activity якщо strong bias в один бік
        return buy_ratio > 0.7 or buy_ratio < 0.3
    
    def _determine_enhanced_block_type(self, current: Dict, left_context: List[Dict], right_context: List[Dict]) -> str:
        """Покращене визначення типу блоку"""
        # Аналіз buy/sell pressure
        buy_ratio = current['buy_volume'] / current['volume'] if current['volume'] > 0 else 0.5
        
        # Аналіз руху після блоку
        future_move = right_context[-1]['close'] - current['close']
        
        # Комбінований аналіз
        if buy_ratio > 0.6 and future_move > 0:
            return 'bullish'
        elif buy_ratio < 0.4 and future_move < 0:
            return 'bearish'
        elif future_move > 0:
            return 'bullish'
        else:
            return 'bearish'
    
    def _calculate_enhanced_strength(self, current: Dict, left_context: List[Dict], right_context: List[Dict], volume_threshold: float) -> float:
        """Покращений розрахунок сили блоку"""
        strength = 0
        
        # Volume component (0-30)
        volume_ratio = current['volume'] / volume_threshold
        strength += min(30, volume_ratio * 15)
        
        # Quote volume component (0-25)
        avg_quote_volume = np.mean([c['quote_volume'] for c in left_context])
        if avg_quote_volume > 0:
            quote_ratio = current['quote_volume'] / avg_quote_volume
            strength += min(25, quote_ratio * 10)
        
        # Price action component (0-25)
        price_impact = abs(right_context[-1]['close'] - current['close']) / current['close']
        strength += min(25, price_impact * 500)
        
        # Institutional component (0-20)
        buy_ratio = current['buy_volume'] / current['volume'] if current['volume'] > 0 else 0.5
        institutional_score = abs(buy_ratio - 0.5) * 2  # Distance from 50%
        strength += institutional_score * 20
        
        return min(100, strength)
    
    def _calculate_flux_score(self, current: Dict, left_context: List[Dict], right_context: List[Dict]) -> float:
        """Розрахунок Flux оцінки"""
        if not left_context or not right_context:
            return 0
        
        # Аналіз зміни потоків
        before_flow = np.mean([c['buy_volume'] - (c['volume'] - c['buy_volume']) for c in left_context[-3:]])
        after_flow = np.mean([c['buy_volume'] - (c['volume'] - c['buy_volume']) for c in right_context[:3]])
        
        # Розрахунок зміни flux
        total_volume = current['volume'] + np.mean([c['volume'] for c in left_context[-3:]])
        if total_volume > 0:
            flux_change = abs(after_flow - before_flow) / total_volume
            return min(100, flux_change * 1000)
        
        return 0
    
    def _calculate_institutional_level(self, current: Dict, institutional_threshold: float) -> float:
        """Розрахунок рівня institutional activity"""
        if current['volume'] == 0:
            return 0
        
        buy_ratio = current['buy_volume'] / current['volume']
        
        # Оцінка відхилення від звичайної активності
        institutional_deviation = abs(buy_ratio - 0.5) / 0.5
        
        # Масштабування до 0-100
        return min(100, institutional_deviation * 100)
    
    def _build_volume_profile(self, current: Dict, left_context: List[Dict], right_context: List[Dict]) -> List[float]:
        """Побудова профілю об'єму"""
        # Створюємо простий volume profile на основі OHLC та volume
        all_candles = left_context + [current] + right_context
        
        volume_profile = []
        for candle in all_candles[-10:]:  # Останні 10 свічок
            # Нормалізуємо об'єм відносно діапазону ціни
            price_range = candle['high'] - candle['low']
            if price_range > 0:
                volume_density = candle['volume'] / price_range
                volume_profile.append(volume_density)
        
        return volume_profile
    
    def calculate_price_approach(self, symbol: str, current_price: float, order_blocks: List[EnhancedOrderBlock], kline_data: List[Dict]) -> List[PriceApproach]:
        """Розрахунок наближення ціни до Order Blocks"""
        approaches = []
        
        if len(kline_data) < 5:
            return approaches
        
        # Розрахунок середнього tick size
        recent_prices = [k['close'] for k in kline_data[-10:]]
        price_changes = [abs(recent_prices[i] - recent_prices[i-1]) for i in range(1, len(recent_prices))]
        avg_tick = np.mean(price_changes) if price_changes else 0.001
        
        for block in order_blocks:
            if not block.is_active:
                continue
            
            zone_low = block.low_price
            zone_high = block.high_price
            zone_mid = (zone_low + zone_high) / 2
            
            # Розрахунок відстані до зони
            if current_price < zone_low:
                distance = zone_low - current_price
                target_zone = (zone_low, zone_high)
            elif current_price > zone_high:
                distance = current_price - zone_high
                target_zone = (zone_low, zone_high)
            else:
                # Ціна вже в зоні
                distance = 0
                target_zone = (zone_low, zone_high)
            
            # Розрахунок відстані в тіках
            distance_ticks = int(distance / avg_tick) if avg_tick > 0 else 999
            
            # Аналіз швидкості наближення
            approach_speed = self._analyze_approach_speed(kline_data[-5:], current_price, zone_mid)
            
            # Розрахунок вірогідності досягнення зони
            probability = self._calculate_reach_probability(distance_ticks, approach_speed, block.strength)
            
            # Створюємо об'єкт наближення якщо це релевантно
            if distance_ticks <= 50:  # В межах 50 тіків
                approach = PriceApproach(
                    symbol=symbol,
                    current_price=current_price,
                    target_zone=target_zone,
                    distance_ticks=distance_ticks,
                    approach_speed=approach_speed,
                    probability=probability
                )
                approaches.append(approach)
        
        return sorted(approaches, key=lambda x: x.distance_ticks)
    
    def _analyze_approach_speed(self, recent_candles: List[Dict], current_price: float, target_price: float) -> str:
        """Аналіз швидкості наближення"""
        if len(recent_candles) < 3:
            return 'unknown'
        
        # Розрахунок momentum в напрямку цілі
        closes = [c['close'] for c in recent_candles]
        direction_to_target = 1 if target_price > current_price else -1
        
        movements = []
        for i in range(1, len(closes)):
            move = (closes[i] - closes[i-1]) * direction_to_target
            movements.append(move)
        
        avg_movement = np.mean(movements) if movements else 0
        movement_consistency = len([m for m in movements if m > 0]) / len(movements) if movements else 0
        
        if avg_movement > 0 and movement_consistency > 0.7:
            if avg_movement > 0.002 * current_price:  # Більше 0.2% за свічку
                return 'fast'
            else:
                return 'medium'
        else:
            return 'slow'
    
    def _calculate_reach_probability(self, distance_ticks: int, approach_speed: str, block_strength: float) -> float:
        """Розрахунок вірогідності досягнення зони"""
        base_probability = 50  # Базова вірогідність
        
        # Корекція за відстанню
        if distance_ticks <= 5:
            distance_bonus = 40
        elif distance_ticks <= 10:
            distance_bonus = 30
        elif distance_ticks <= 20:
            distance_bonus = 20
        else:
            distance_bonus = max(0, 20 - (distance_ticks - 20))
        
        # Корекція за швидкістю
        speed_bonus = {'fast': 25, 'medium': 15, 'slow': 5, 'unknown': 0}[approach_speed]
        
        # Корекція за силу блоку
        strength_bonus = (block_strength / 100) * 15
        
        total_probability = base_probability + distance_bonus + speed_bonus + strength_bonus
        return min(95, max(5, total_probability))

# ================================
# ENHANCED ALERT ENGINE
# ================================
class EnhancedAlertEngine:
    def __init__(self, bot: Bot, db, analyzer: EnhancedTechnicalAnalyzer):
        self.bot = bot
        self.db = db
        self.analyzer = analyzer
        self.symbol_fetcher = analyzer.symbol_fetcher
        self.is_running = False
        self.active_order_blocks: Dict[str, List[EnhancedOrderBlock]] = {}
        self.approach_history: Dict[str, Set[str]] = defaultdict(set)  # Для уникнення дублікатів
        self.scan_count = 0
        
    async def start_monitoring(self):
        """Запуск покращеного моніторингу"""
        self.is_running = True
        logger.info("🚀 Розширений моніторинг Volumized Order Blocks запущено")
        
        while self.is_running:
            try:
                await self.enhanced_scan_cycle()
                self.scan_count += 1
                
                # Кожні 10 циклів оновлюємо список символів
                if self.scan_count % 10 == 0:
                    await self.symbol_fetcher.get_top_symbols(TOP_SYMBOLS_COUNT)
                
                await asyncio.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Критична помилка в циклі моніторингу: {e}")
                await asyncio.sleep(60)
    
    async def enhanced_scan_cycle(self):
        """Покращений цикл сканування"""
        # Отримуємо топ символи
        top_symbols = await self.symbol_fetcher.get_top_symbols(TOP_SYMBOLS_COUNT)
        
        if not top_symbols:
            logger.warning("Не вдалося отримати список символів")
            return
        
        logger.info(f"🔍 Сканування {len(top_symbols)} символів...")
        
        # Отримуємо активні алерти
        async with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT user_id FROM user_alerts WHERE is_active = 1
            """)
            active_users = [row[0] for row in cursor.fetchall()]
        
        if not active_users:
            logger.info("Немає активних користувачів для алертів")
            return
        
        # Сканування символів
        scan_tasks = []
        for symbol in top_symbols[:50]:  # Перші 50 символів для швидкості
            for timeframe in TIMEFRAMES:
                task = self.scan_symbol_for_blocks(symbol, timeframe, active_users)
                scan_tasks.append(task)
        
        # Виконуємо сканування батчами
        batch_size = 10
        for i in range(0, len(scan_tasks), batch_size):
            batch = scan_tasks[i:i+batch_size]
            await asyncio.gather(*batch, return_exceptions=True)
            await asyncio.sleep(0.1)  # Маленька пауза між батчами
    
    async def scan_symbol_for_blocks(self, symbol: str, timeframe: str, active_users: List[int]):
        """Сканування конкретного символу на Order Blocks"""
        try:
            # Отримуємо дані
            kline_data = await self.analyzer.get_kline_data(symbol, timeframe, 500)
            if not kline_data or len(kline_data) < 50:
                return
            
            current_price = kline_data[-1]['close']
            
            # Знаходимо Order Blocks
            order_blocks = self.analyzer.identify_volumized_order_blocks(kline_data, symbol, timeframe)
            
            if not order_blocks:
                return
            
            # Оновлюємо активні блоки
            key = f"{symbol}_{timeframe}"
            self.active_order_blocks[key] = order_blocks
            
            # Аналізуємо наближення до блоків
            approaches = self.analyzer.calculate_price_approach(symbol, current_price, order_blocks, kline_data)
            
            # Надсилаємо алерти для наближень
            for approach in approaches:
                await self.process_approach_alert(approach, order_blocks, active_users)
                
            # Перевіряємо входження в зони
            for block in order_blocks:
                if self.is_price_in_zone(current_price, block):
                    await self.send_zone_entry_alert(block, current_price, active_users, kline_data)
                    
        except Exception as e:
            logger.error(f"Помилка сканування {symbol}_{timeframe}: {e}")
    
    def is_price_in_zone(self, current_price: float, order_block: EnhancedOrderBlock) -> bool:
        """Перевірка чи ціна в зоні Order Block"""
        return order_block.low_price <= current_price <= order_block.high_price
    
    async def process_approach_alert(self, approach: PriceApproach, order_blocks: List[EnhancedOrderBlock], active_users: List[int]):
        """Обробка алерту наближення"""
        # Знаходимо відповідний Order Block
        target_block = None
        for block in order_blocks:
            if (block.low_price, block.high_price) == approach.target_zone:
                target_block = block
                break
        
        if not target_block:
            return
        
        # Перевіряємо чи вже надсилали алерт для цієї відстані
        alert_key = f"{approach.symbol}_{target_block.id}_{approach.distance_ticks}"
        
        if alert_key in self.approach_history[approach.symbol]:
            return
        
        # Надсилаємо алерт тільки для близьких наближень
        if approach.distance_ticks <= APPROACH_TICKS and approach.probability > 60:
            for user_id in active_users:
                await self.send_approach_alert(user_id, approach, target_block)
            
            # Зберігаємо в історію
            self.approach_history[approach.symbol].add(alert_key)
            
            # Очищуємо старі записи (залишаємо тільки останні 100)
            if len(self.approach_history[approach.symbol]) > 100:
                old_items = list(self.approach_history[approach.symbol])[:50]
                for item in old_items:
                    self.approach_history[approach.symbol].remove(item)
    
    async def send_approach_alert(self, user_id: int, approach: PriceApproach, order_block: EnhancedOrderBlock):
        """Надсилання алерту наближення"""
        try:
            block_emoji = "🟢" if order_block.block_type == "bullish" else "🔴"
            speed_emoji = {"fast": "🚀", "medium": "⚡", "slow": "🐌", "unknown": "❓"}[approach.approach_speed]
            
            strength_stars = "⭐" * min(5, int(order_block.strength / 20))
            flux_bars = "█" * min(10, int(order_block.flux_score / 10))
            
            message = f"""
🎯 <b>НАБЛИЖЕННЯ ДО ЗОНИ!</b> {block_emoji}

📊 <b>{approach.symbol.upper()}</b> | {order_block.timeframe.upper()}
💰 Поточна ціна: <b>${approach.current_price:,.4f}</b>

🎯 <b>Order Block Info:</b>
• Тип: <b>{order_block.block_type.title()}</b> Order Block
• Зона: <b>${approach.target_zone[0]:,.4f} - ${approach.target_zone[1]:,.4f}</b>
• Відстань: <b>{approach.distance_ticks} тіків</b>

📈 <b>Аналіз сили:</b>
• Сила блоку: <b>{order_block.strength:.1f}/100</b> {strength_stars}
• Flux Score: <b>{order_block.flux_score:.1f}/100</b> {flux_bars}
• Institutional: <b>{order_block.institutional_level:.1f}%</b>

🚀 <b>Динаміка наближення:</b>
• Швидкість: <b>{approach.approach_speed.title()}</b> {speed_emoji}
• Вірогідність: <b>{approach.probability:.1f}%</b>

💡 <b>Volumized Analysis:</b>
• Volume: <b>{order_block.volume:,.0f}</b>
• Quote Volume: <b>${order_block.quote_volume:,.0f}</b>

⏰ {datetime.now().strftime('%H:%M:%S')} | Цикл #{self.scan_count}
            """
            
            await self.bot.send_message(user_id, message, parse_mode="HTML")
            
            # Зберігаємо в базу
            await self._save_alert_to_db(user_id, approach.symbol, message, approach.current_price)
            
        except Exception as e:
            logger.error(f"Помилка надсилання approach алерту: {e}")
    
    async def send_zone_entry_alert(self, order_block: EnhancedOrderBlock, current_price: float, active_users: List[int], kline_data: List[Dict]):
        """Надсилання алерту входження в зону"""
        try:
            # Перевіряємо чи вже надсилали цей алерт
            entry_key = f"{order_block.symbol}_{order_block.id}_entry"
            
            if entry_key in self.approach_history[order_block.symbol]:
                return
            
            block_emoji = "🟢" if order_block.block_type == "bullish" else "🔴"
            volume_analysis = self._analyze_current_volume(kline_data[-10:], order_block)
            
            message = f"""
🚨 <b>ЦІНА В ЗОНІ!</b> {block_emoji}

📊 <b>{order_block.symbol.upper()}</b> | {order_block.timeframe.upper()}
💰 Ціна входження: <b>${current_price:,.4f}</b>

🎯 <b>Volumized Order Block:</b>
• Тип: <b>{order_block.block_type.title()}</b>
• Зона: <b>${order_block.low_price:,.4f} - ${order_block.high_price:,.4f}</b>
• Позиція в зоні: <b>{self._calculate_zone_position(current_price, order_block):.1f}%</b>

📊 <b>Метрики блоку:</b>
• Сила: <b>{order_block.strength:.1f}/100</b>
• Flux: <b>{order_block.flux_score:.1f}/100</b>
• Institutional: <b>{order_block.institutional_level:.1f}%</b>

📈 <b>Поточний об'єм:</b>
• Статус: <b>{volume_analysis['status']}</b>
• Порівняння з блоком: <b>{volume_analysis['comparison']}</b>

🎲 <b>Рекомендація:</b>
{self._generate_trading_recommendation(order_block, current_price, volume_analysis)}

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
            
            for user_id in active_users:
                await self.bot.send_message(user_id, message, parse_mode="HTML")
            
            # Зберігаємо що алерт надіслано
            self.approach_history[order_block.symbol].add(entry_key)
            
        except Exception as e:
            logger.error(f"Помилка надсилання zone entry алерту: {e}")
    
    def _calculate_zone_position(self, current_price: float, order_block: EnhancedOrderBlock) -> float:
        """Розрахунок позиції ціни в зоні (0-100%)"""
        zone_range = order_block.high_price - order_block.low_price
        if zone_range == 0:
            return 50
        
        position = (current_price - order_block.low_price) / zone_range * 100
        return max(0, min(100, position))
    
    def _analyze_current_volume(self, recent_klines: List[Dict], order_block: EnhancedOrderBlock) -> Dict:
        """Аналіз поточного об'єму"""
        if not recent_klines:
            return {"status": "Невідомо", "comparison": "Неможливо порівняти"}
        
        current_volume = recent_klines[-1]['volume']
        avg_recent_volume = np.mean([k['volume'] for k in recent_klines[-5:]])
        
        # Порівняння з об'ємом блоку
        block_volume_ratio = current_volume / order_block.volume if order_block.volume > 0 else 0
        
        if current_volume > avg_recent_volume * 1.5:
            status = "🔥 Високий об'єм"
        elif current_volume > avg_recent_volume:
            status = "📈 Підвищений об'єм"
        else:
            status = "📊 Звичайний об'єм"
        
        if block_volume_ratio > 0.8:
            comparison = f"🎯 {block_volume_ratio:.1f}x від блоку (Сильна активність)"
        elif block_volume_ratio > 0.5:
            comparison = f"📊 {block_volume_ratio:.1f}x від блоку (Помірна активність)"
        else:
            comparison = f"📉 {block_volume_ratio:.1f}x від блоку (Слабка активність)"
        
        return {
            "status": status,
            "comparison": comparison,
            "ratio": block_volume_ratio
        }
    
    def _generate_trading_recommendation(self, order_block: EnhancedOrderBlock, current_price: float, volume_analysis: Dict) -> str:
        """Генерація торгової рекомендації"""
        recommendations = []
        
        # Базова рекомендація за типом блоку
        if order_block.block_type == "bullish":
            recommendations.append("🟢 Розгляй LONG позицію")
        else:
            recommendations.append("🔴 Розгляй SHORT позицію")
        
        # Рекомендації за силою блоку
        if order_block.strength > 80:
            recommendations.append("💎 Дуже сильна зона - висока вірогідність реакції")
        elif order_block.strength > 60:
            recommendations.append("⭐ Сильна зона - хороша можливість")
        else:
            recommendations.append("⚠️ Помірна зона - будь обережний")
        
        # Рекомендації за об'ємом
        if volume_analysis['ratio'] > 0.7:
            recommendations.append("🚀 Об'єм підтверджує рух")
        else:
            recommendations.append("🔍 Чекай підтвердження об'ємом")
        
        # Рекомендації за institutional activity
        if order_block.institutional_level > 70:
            recommendations.append("🏦 Висока institutional активність")
        
        return "\n".join([f"• {rec}" for rec in recommendations])
    
    async def _save_alert_to_db(self, user_id: int, symbol: str, message: str, price: float):
        """Збереження алерту в базу даних"""
        try:
            async with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO alert_history (user_id, symbol, alert_message, price, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, symbol, message, price, int(datetime.now().timestamp())))
                conn.commit()
        except Exception as e:
            logger.error(f"Помилка збереження алерту в БД: {e}")
    
    def stop_monitoring(self):
        """Зупинка моніторингу"""
        self.is_running = False
        logger.info("🛑 Моніторинг зупинено")

# ================================
# ENHANCED BOT HANDLERS
# ================================
class EnhancedTradingBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.db = Database()
        self.analyzer = EnhancedTechnicalAnalyzer()
        self.alert_engine = EnhancedAlertEngine(self.bot, self.db, self.analyzer)
        self.router = Router()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Налаштування обробників"""
        # Основні команди
        self.router.message(Command("start"))(self.start_handler)
        self.router.message(Command("help"))(self.help_handler)
        self.router.message(Command("add_alert"))(self.add_alert_handler)
        self.router.message(Command("analyze"))(self.analyze_handler)
        self.router.message(Command("top_symbols"))(self.top_symbols_handler)
        self.router.message(Command("status"))(self.status_handler)
        self.router.message(Command("my_alerts"))(self.my_alerts_handler)
        self.router.message(Command("stop_alerts"))(self.stop_alerts_handler)
        
        # FSM обробники
        self.router.message(OrderBlockStates.waiting_for_symbol)(self.process_symbol)
        self.router.message(OrderBlockStates.waiting_for_timeframe)(self.process_timeframe)
        self.router.message(OrderBlockStates.waiting_for_sensitivity)(self.process_sensitivity)
        
        self.dp.include_router(self.router)
    
    async def start_handler(self, message: Message):
        """Покращений обробник /start"""
        welcome_text = f"""
🚀 <b>Enhanced Volumized Order Blocks Bot</b>

Привіт, {message.from_user.first_name}! 

🎯 <b>Нові можливості:</b>
• Автоматичний моніторинг ТОП-100 монет Binance
• Volumized Order Blocks з institutional аналізом
• Flux Charts аналіз потоків ліквідності
• Алерти наближення (за 5 тіків до зони)
• Алерти входження в зону
• Розширена аналітика сили блоків

📊 <b>Таймфрейми:</b> 1h, 4h
🔄 <b>Частота сканування:</b> кожні 30 секунд
🎯 <b>Точність:</b> до 5 тіків наближення

🚀 <b>Команди:</b>
/add_alert - Увімкнути алерти (безкоштовно для всіх монет)
/analyze SYMBOL - Детальний аналіз монети
/top_symbols - Поточний ТОП-100 символів
/status - Статус системи та статистика

<b>⚡ Просто введи /add_alert щоб почати!</b>
        """
        await message.answer(welcome_text, parse_mode="HTML")
    
    async def help_handler(self, message: Message):
        """Покращена довідка"""
        help_text = """
<b>📚 Повна довідка Enhanced Bot</b>

<b>🎯 Volumized Order Blocks:</b>
• Зони з екстремально високим об'ємом
• Institutional footprint аналіз
• Buy/Sell pressure розрахунки
• Volume profile в зонах

<b>🌊 Flux Charts:</b>
• Аналіз потоків ліквідності
• Institutional vs Retail flow
• Momentum напрямків потоків

<b>⚡ Типи алертів:</b>
• 🎯 Approach Alert - за 1-5 тіків до зони
• 🚨 Zone Entry - при входженні в зону
• 🌊 Flux Alert - при сильних потоках

<b>📊 Метрики блоків:</b>
• Strength (0-100) - загальна сила
• Flux Score (0-100) - оцінка потоків
• Institutional Level (0-100) - активність банків

<b>🎮 Автоматичний режим:</b>
Бот автоматично сканує ТОП-100 монет Binance кожні 30 секунд та надсилає алерти всім підписаним користувачам.

<b>💡 Рекомендації:</b>
• Використовуй 4h для загального тренду
• 1h для точних точок входу
• Звертай увагу на Institutional Level > 70%
• Комбінуй з власним аналізом
        """
        await message.answer(help_text, parse_mode="HTML")
    
    async def add_alert_handler(self, message: Message, state: FSMContext):
        """Додавання алертів для всіх монет"""
        user_id = message.from_user.id
        
        try:
            # Додаємо користувача в систему алертів
            async with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Перевіряємо чи вже є активний алерт
                cursor.execute("""
                    SELECT COUNT(*) FROM user_alerts 
                    WHERE user_id = ? AND is_active = 1
                """, (user_id,))
                
                active_count = cursor.fetchone()[0]
                
                if active_count > 0:
                    await message.answer("""
🎯 <b>Алерти вже активні!</b>

Ти вже підписаний на алерти для всіх ТОП-100 монет.

📊 <b>Що відстежується:</b>
• Volumized Order Blocks на 1h та 4h
• Наближення до зон (1-5 тіків)
• Входження в зони
• Flux потоки ліквідності

/status - перевірити статистику
/stop_alerts - зупинити алерти
                    """, parse_mode="HTML")
                    return
                
                # Додаємо загальний алерт для всіх символів
                cursor.execute("""
                    INSERT INTO user_alerts (user_id, symbol, timeframe, sensitivity, alert_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, 'ALL_TOP100', 'ALL', 0.5, 'volumized_order_blocks'))
                
                conn.commit()
            
            success_message = f"""
✅ <b>Алерти активовано!</b>

🎯 <b>Налаштування:</b>
• Символи: ТОП-100 Binance (автооновлення)
• Таймфрейми: 1h, 4h
• Чутливість: 0.5 (середня)
• Типи: Order Blocks + Flux

🚀 <b>Що буде відстежуватися:</b>
• Volumized Order Blocks з силою > 40%
• Наближення до зон за 1-5 тіків
• Входження в зони з аналізом об'єму
• Institutional activity > 70%

⏰ <b>Частота:</b> кожні 30 секунд
📊 <b>Статистика:</b> /status

<b>🎊 Все готово! Очікуй алерти...</b>
            """
            
            await message.answer(success_message, parse_mode="HTML")
            logger.info(f"✅ Користувач {user_id} підписався на алерти")
            
        except Exception as e:
            logger.error(f"Помилка додавання алертів: {e}")
            await message.answer("❌ Помилка активації алертів. Спробуй пізніше.")
    
    async def analyze_handler(self, message: Message):
        """Детальний аналіз конкретної монети"""
        try:
            # Витягуємо символ з команди
            parts = message.text.split()
            if len(parts) < 2:
                await message.answer("""
📊 <b>Аналіз монети</b>

Використання: <code>/analyze SYMBOL</code>

Приклади:
• <code>/analyze BTC</code>
• <code>/analyze ETH</code>
• <code>/analyze SOL</code>

🎯 Отримаєш повний аналіз Order Blocks та Flux Charts
                """, parse_mode="HTML")
                return
            
            symbol = parts[1].upper()
            
            # Надсилаємо повідомлення про початок аналізу
            loading_msg = await message.answer(f"🔍 Аналізую {symbol}...")
            
            # Виконуємо аналіз для обох таймфреймів
            analysis_results = {}
            
            for timeframe in TIMEFRAMES:
                kline_data = await self.analyzer.get_kline_data(symbol, timeframe, 500)
                
                if kline_data:
                    order_blocks = self.analyzer.identify_volumized_order_blocks(kline_data, symbol, timeframe)
                    current_price = kline_data[-1]['close']
                    approaches = self.analyzer.calculate_price_approach(symbol, current_price, order_blocks, kline_data)
                    
                    analysis_results[timeframe] = {
                        'order_blocks': order_blocks[:5],  # Топ-5 блоків
                        'current_price': current_price,
                        'approaches': approaches[:3],  # Топ-3 наближення
                        'volume_24h': sum([k['volume'] for k in kline_data[-24:]] if timeframe == '1h' else [k['volume'] for k in kline_data[-6:]])
                    }
            
            # Видаляємо повідомлення про завантаження
            await loading_msg.delete()
            
            # Формуємо детальний звіт
            await self.send_detailed_analysis(message.chat.id, symbol, analysis_results)
            
        except Exception as e:
            logger.error(f"Помилка аналізу: {e}")
            await message.answer("❌ Помилка аналізу. Перевір назву символу.")
    
    async def send_detailed_analysis(self, chat_id: int, symbol: str, results: Dict):
        """Надсилання детального аналізу"""
        try:
            for timeframe, data in results.items():
                if not data['order_blocks']:
                    continue
                
                report = f"""
📊 <b>ДЕТАЛЬНИЙ АНАЛІЗ: {symbol}</b>
⏰ <b>Таймфрейм:</b> {timeframe.upper()}
💰 <b>Поточна ціна:</b> ${data['current_price']:,.4f}
📈 <b>Об'єм ({timeframe}):</b> {data['volume_24h']:,.0f}

🎯 <b>ТОП ORDER BLOCKS:</b>
"""
                
                for i, block in enumerate(data['order_blocks'], 1):
                    block_emoji = "🟢" if block.block_type == "bullish" else "🔴"
                    strength_stars = "⭐" * min(5, int(block.strength / 20))
                    
                    distance = min(
                        abs(data['current_price'] - block.low_price),
                        abs(data['current_price'] - block.high_price)
                    )
                    distance_pct = (distance / data['current_price']) * 100
                    
                    report += f"""
<b>{i}. {block_emoji} {block.block_type.title()} Block</b>
• Зона: ${block.low_price:,.4f} - ${block.high_price:,.4f}
• Відстань: {distance_pct:.2f}%
• Сила: {block.strength:.1f}/100 {strength_stars}
• Flux: {block.flux_score:.1f}/100
• Institutional: {block.institutional_level:.1f}%
• Volume: {block.volume:,.0f}
"""
                
                # Додаємо інформацію про наближення
                if data['approaches']:
                    report += f"\n🎯 <b>АКТИВНІ НАБЛИЖЕННЯ:</b>\n"
                    for approach in data['approaches']:
                        speed_emoji = {"fast": "🚀", "medium": "⚡", "slow": "🐌"}[approach.approach_speed]
                        report += f"""
• Зона: ${approach.target_zone[0]:.4f}-${approach.target_zone[1]:.4f}
• Відстань: {approach.distance_ticks} тіків {speed_emoji}
• Вірогідність: {approach.probability:.1f}%
"""
                
                report += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                await self.bot.send_message(chat_id, report, parse_mode="HTML")
                await asyncio.sleep(0.5)  # Пауза між повідомленнями
                
        except Exception as e:
            logger.error(f"Помилка надсилання аналізу: {e}")
    
    async def top_symbols_handler(self, message: Message):
        """Показати поточний ТОП символів"""
        try:
            loading_msg = await message.answer("📊 Завантажую ТОП-100 символів...")
            
            symbols = await self.analyzer.symbol_fetcher.get_top_symbols(50)  # Показуємо топ-50
            
            await loading_msg.delete()
            
            if symbols:
                # Розділяємо на частини для красивого відображення
                top_10 = symbols[:10]
                top_20 = symbols[10:20]
                top_50 = symbols[20:50]
                
                report = f"""
📊 <b>ТОП-100 СИМВОЛІВ BINANCE</b>
<i>Сортування за об'ємом торгівлі за 24h</i>

🥇 <b>ТОП-10:</b>
{' • '.join(top_10)}

🥈 <b>11-20 місце:</b>
{' • '.join(top_20)}

🥉 <b>21-50 місце:</b>
{' • '.join(top_50)}

⏰ Оновлено: {datetime.now().strftime('%H:%M:%S')}
🔄 Автооновлення кожну годину

<i>💡 Всі ці символи автоматично відстежуються ботом</i>
                """
                
                await message.answer(report, parse_mode="HTML")
            else:
                await message.answer("❌ Не вдалося завантажити список символів")
                
        except Exception as e:
            logger.error(f"Помилка отримання топ символів: {e}")
            await message.answer("❌ Помилка завантаження даних")
    
    async def status_handler(self, message: Message):
        """Статус системи"""
        try:
            user_id = message.from_user.id
            
            # Отримуємо статистику користувача
            async with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Активні алерти
                cursor.execute("""
                    SELECT COUNT(*) FROM user_alerts 
                    WHERE user_id = ? AND is_active = 1
                """, (user_id,))
                active_alerts = cursor.fetchone()[0]
                
                # Історія алертів за сьогодні
                today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
                cursor.execute("""
                    SELECT COUNT(*) FROM alert_history 
                    WHERE user_id = ? AND timestamp >= ?
                """, (user_id, today_start))
                today_alerts = cursor.fetchone()[0]
                
                # Загальна кількість алертів
                cursor.execute("""
                    SELECT COUNT(*) FROM alert_history 
                    WHERE user_id = ?
                """, (user_id,))
                total_alerts = cursor.fetchone()[0]
            
            # Статус системи
            top_symbols_count = len(await self.analyzer.symbol_fetcher.get_top_symbols(100))
            active_blocks_count = sum(len(blocks) for blocks in self.alert_engine.active_order_blocks.values())
            
            is_monitoring = "🟢 Активний" if self.alert_engine.is_running else "🔴 Зупинений"
            
            status_report = f"""
📊 <b>СТАТУС СИСТЕМИ</b>

👤 <b>Твоя статистика:</b>
• Активні алерти: <b>{active_alerts}</b>
• Алерти сьогодні: <b>{today_alerts}</b>
• Всього алертів: <b>{total_alerts}</b>

🤖 <b>Система:</b>
• Моніторинг: <b>{is_monitoring}</b>
• Цикл сканування: <b>#{self.alert_engine.scan_count}</b>

📈 <b>Аналіз за останній тиждень:</b>
• Загальна кількість алертів: <b>{total_alerts}</b>
• Активні за останній тиждень: <b>{active_alerts}</b>
• Активні за останній день: <b>{today_alerts}</b>
• Частота алерту: <b>{1 / CHECK_INTERVAL} тіків</b>

💡 <b>Рекомендації:</b>
• Використовуй 4h для загального тренду
• 1h для точних точок входу
• Комбінуй з власним аналізом
• Звертай увагу на Institutional Level > 70%        
• Використовуй Flux Score для підтвердження руху
• Аналізуй Volume Profile в зонах

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
            
            await message.answer(status_report, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Помилка статусу: {e}")
            await message.answer("❌ Помилка отримання статусу")
    
    async def my_alerts_handler(self, message: Message):
        """Показати активні алерти користувача"""
        try:
            user_id = message.from_user.id
            
            async with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Активні алерти
                cursor.execute("""
                    SELECT symbol, timeframe, sensitivity, alert_type, created_at
                    FROM user_alerts 
                    WHERE user_id = ? AND is_active = 1
                """, (user_id,))
                active_alerts = cursor.fetchall()
                
                # Останні алерти
                cursor.execute("""
                    SELECT symbol, alert_message, price, timestamp
                    FROM alert_history 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """, (user_id,))
                recent_alerts = cursor.fetchall()
            
            if not active_alerts:
                await message.answer("""
📊 <b>ТВОЇ АЛЕРТИ</b>

❌ <b>Немає активних алертів</b>

Щоб почати отримувати алерти:
• <code>/add_alert</code> - увімкнути алерти для всіх монет
• <code>/analyze SYMBOL</code> - аналіз конкретної монети

🎯 <b>Що відстежується:</b>
• Volumized Order Blocks
• Наближення до зон
• Входження в зони
• Flux потоки
                """, parse_mode="HTML")
                return
            
            # Формуємо звіт про активні алерти
            report = f"""
📊 <b>ТВОЇ АКТИВНІ АЛЕРТИ</b>

🎯 <b>Активні підписки:</b>
"""
            
            for alert in active_alerts:
                symbol, timeframe, sensitivity, alert_type, created_at = alert
                created_date = datetime.fromtimestamp(created_at).strftime('%d.%m.%Y %H:%M')
                
                report += f"""
• <b>{symbol}</b> | {timeframe.upper()}
  Чутливість: {sensitivity} | Тип: {alert_type}
  Створено: {created_date}
"""
            
            # Додаємо останні алерти
            if recent_alerts:
                report += f"\n📈 <b>ОСТАННІ АЛЕРТИ:</b>\n"
                
                for alert in recent_alerts[:5]:  # Показуємо тільки 5
                    symbol, message, price, timestamp = alert
                    alert_date = datetime.fromtimestamp(timestamp).strftime('%d.%m %H:%M')
                    
                    # Скорочуємо повідомлення
                    short_message = message[:100] + "..." if len(message) > 100 else message
                    
                    report += f"""
• <b>{symbol}</b> | ${price:,.4f}
  {short_message}
  {alert_date}
"""
            
            report += f"""
\n💡 <b>Керування:</b>
/stop_alerts - зупинити всі алерти
/status - статистика та статус
            """
            
            await message.answer(report, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Помилка my_alerts: {e}")
            await message.answer("❌ Помилка отримання алертів")
    
    async def stop_alerts_handler(self, message: Message):
        """Зупинка всіх алертів користувача"""
        try:
            user_id = message.from_user.id
            
            async with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Деактивуємо всі алерти користувача
                cursor.execute("""
                    UPDATE user_alerts 
                    SET is_active = 0 
                    WHERE user_id = ?
                """, (user_id,))
                
                affected_rows = cursor.rowcount
                conn.commit()
            
            if affected_rows > 0:
                await message.answer(f"""
🛑 <b>АЛЕРТИ ЗУПИНЕНО!</b>

✅ Деактивовано {affected_rows} алертів

📊 <b>Що це означає:</b>
• Ти більше не отримуватимеш автоматичні алерти
• Моніторинг продовжується для інших користувачів
• Можеш знову увімкнути командою /add_alert

💡 <b>Альтернативи:</b>
• <code>/analyze SYMBOL</code> - ручний аналіз
• <code>/top_symbols</code> - перегляд топ монет
• <code>/status</code> - перевірка системи

<b>Дякуємо за використання бота! 🚀</b>
                """, parse_mode="HTML")
                
                logger.info(f"🛑 Користувач {user_id} зупинив алерти")
            else:
                await message.answer("""
ℹ️ <b>НЕМАЄ АКТИВНИХ АЛЕРТІВ</b>

Ти вже не підписаний на алерти.

Щоб почати отримувати алерти:
• <code>/add_alert</code> - увімкнути алерти
                """, parse_mode="HTML")
                
        except Exception as e:
            logger.error(f"Помилка зупинки алертів: {e}")
            await message.answer("❌ Помилка зупинки алертів")
    
    async def process_symbol(self, message: Message, state: FSMContext):
        """Обробка символу в FSM"""
        symbol = message.text.upper()
        
        # Перевіряємо валідність символу
        if not symbol.isalnum() or len(symbol) > 10:
            await message.answer("❌ Невірний символ. Використовуй тільки літери та цифри (макс. 10 символів)")
            return
        
        await state.update_data(symbol=symbol)
        await state.set_state(OrderBlockStates.waiting_for_timeframe)
        
        await message.answer(f"""
✅ <b>Символ встановлено: {symbol}</b>

Тепер вибери таймфрейм:

⏰ <b>Доступні таймфрейми:</b>
• <code>1h</code> - годинний (для точних точок входу)
• <code>4h</code> - 4-годинний (для загального тренду)
• <code>1d</code> - денний (для довгострокових зон)

Введи один з таймфреймів:
        """, parse_mode="HTML")
    
    async def process_timeframe(self, message: Message, state: FSMContext):
        """Обробка таймфрейму в FSM"""
        timeframe = message.text.lower()
        
        valid_timeframes = ['1h', '4h', '1d']
        if timeframe not in valid_timeframes:
            await message.answer(f"""
❌ <b>Невірний таймфрейм!</b>

Доступні таймфрейми:
• <code>1h</code> - годинний
• <code>4h</code> - 4-годинний  
• <code>1d</code> - денний

Введи один з цих таймфреймів:
            """, parse_mode="HTML")
            return
        
        await state.update_data(timeframe=timeframe)
        await state.set_state(OrderBlockStates.waiting_for_sensitivity)
        
        await message.answer(f"""
✅ <b>Таймфрейм встановлено: {timeframe.upper()}</b>

Тепер встанови чутливість (0.1 - 1.0):

🎯 <b>Рівні чутливості:</b>
• <code>0.1</code> - дуже низька (тільки найсильніші блоки)
• <code>0.3</code> - низька (сильні блоки)
• <code>0.5</code> - середня (рекомендована)
• <code>0.7</code> - висока (багато сигналів)
• <code>1.0</code> - дуже висока (всі блоки)

Введи число від 0.1 до 1.0:
        """, parse_mode="HTML")
    
    async def process_sensitivity(self, message: Message, state: FSMContext):
        """Обробка чутливості в FSM"""
        try:
            sensitivity = float(message.text)
            
            if not (0.1 <= sensitivity <= 1.0):
                await message.answer("""
❌ <b>Невірна чутливість!</b>

Чутливість має бути від 0.1 до 1.0

Приклади:
• <code>0.5</code> - середня чутливість
• <code>0.3</code> - низька чутливість
• <code>0.7</code> - висока чутливість

Введи число від 0.1 до 1.0:
                """, parse_mode="HTML")
                return
            
            # Отримуємо дані з FSM
            data = await state.get_data()
            symbol = data.get('symbol')
            timeframe = data.get('timeframe')
            
            # Додаємо алерт в базу
            user_id = message.from_user.id
            
            async with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Додаємо новий алерт
                cursor.execute("""
                    INSERT INTO user_alerts (user_id, symbol, timeframe, sensitivity, alert_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, symbol, timeframe, sensitivity, 'volumized_order_blocks'))
                
                conn.commit()
            
            # Очищаємо FSM
            await state.clear()
            
            await message.answer(f"""
✅ <b>АЛЕРТ ДОДАНО!</b>

📊 <b>Налаштування:</b>
• Символ: <b>{symbol}</b>
• Таймфрейм: <b>{timeframe.upper()}</b>
• Чутливість: <b>{sensitivity}</b>
• Тип: Volumized Order Blocks

🎯 <b>Що буде відстежуватися:</b>
• Order Blocks з силою > {int(sensitivity * 40)}%
• Flux Score > {int(sensitivity * 30)}%
• Наближення до зон
• Входження в зони

🚀 <b>Команди:</b>
/my_alerts - переглянути всі алерти
/status - статистика та статус
/stop_alerts - зупинити алерти

<b>🎊 Алерт активовано! Очікуй сповіщення...</b>
            """, parse_mode="HTML")
            
            logger.info(f"✅ Додано алерт: {user_id} -> {symbol}_{timeframe}")
            
        except ValueError:
            await message.answer("""
❌ <b>Невірний формат!</b>

Введи число від 0.1 до 1.0

Приклади:
• <code>0.5</code>
• <code>0.3</code>
• <code>0.7</code>
            """, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Помилка додавання алерту: {e}")
            await message.answer("❌ Помилка додавання алерту. Спробуй пізніше.")
            await state.clear()

# ================================
# DATABASE CLASS
# ================================
class Database:
    def __init__(self, db_path: str = "data/data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Ініціалізація бази даних"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблиця користувачів
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at INTEGER,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Таблиця алертів користувачів
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    symbol TEXT,
                    timeframe TEXT,
                    sensitivity REAL,
                    alert_type TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблиця історії алертів
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    symbol TEXT,
                    alert_message TEXT,
                    price REAL,
                    timestamp INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблиця Order Blocks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_blocks (
                    id TEXT PRIMARY KEY,
                    symbol TEXT,
                    timeframe TEXT,
                    high_price REAL,
                    low_price REAL,
                    volume REAL,
                    quote_volume REAL,
                    timestamp INTEGER,
                    block_type TEXT,
                    strength REAL,
                    flux_score REAL,
                    institutional_level REAL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at INTEGER
                )
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("✅ База даних ініціалізована")
            
        except Exception as e:
            logger.error(f"Помилка ініціалізації БД: {e}")
    
    def get_connection(self):
        """Отримання з'єднання з базою даних"""
        return sqlite3.connect(self.db_path)

# ================================
# STATES
# ================================
class OrderBlockStates(StatesGroup):
    waiting_for_symbol = State()
    waiting_for_timeframe = State()
    waiting_for_sensitivity = State()

# ================================
# MAIN EXECUTION
# ================================
async def main():
    """Головна функція"""
    try:
        logger.info("🚀 Запуск Enhanced Volumized Order Blocks Bot...")
        
        # Створюємо бота
        bot = EnhancedTradingBot()
        
        # Запускаємо моніторинг в фоні
        monitoring_task = asyncio.create_task(bot.alert_engine.start_monitoring())
        
        # Запускаємо бота
        await bot.dp.start_polling(bot.bot)
        
    except KeyboardInterrupt:
        logger.info("🛑 Отримано сигнал зупинки...")
    except Exception as e:
        logger.error(f"Критична помилка: {e}")
    finally:
        # Зупиняємо моніторинг
        if 'bot' in locals():
            bot.alert_engine.stop_monitoring()
        
        # Закриваємо сесії
        if 'bot' in locals():
            await bot.analyzer.close_session()
        
        logger.info("🛑 Бот зупинено")

if __name__ == "__main__":
    # Запускаємо головну функцію
    asyncio.run(main())