import psycopg2
from psycopg2 import sql, errors
from datetime import datetime
import configparser
 
config = configparser.ConfigParser()
config.read('config.ini', encoding = 'utf-8')
 
password = config['configs']['password']
 
# Здесь описаны настройки подключения к БД
DB_CONFIG = {
    "database": "bd_translate_bot",
    "user": "postgres",
    "password": password,
    "host": "localhost",
    "port": "5432"
}
 
def create_database():
    """
    Функция, которая создает таблицы в базе данных с учетом сохранения прогресса
    Всего в БД 5 таблицы:
    Пользователи
    Слова
    Связующая таблица для Пользователей и слов
    Удаленные пользователями слова
    Таблица, сохраняющая историю
    """
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        # Таблица пользователей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users(
            id BIGINT PRIMARY KEY,
            name VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW(),
            last_active TIMESTAMP DEFAULT NOW()
            );
        """)
 
        # Таблица слов (добавляем user_id)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS words(
            id SERIAL PRIMARY KEY,
            russian_word VARCHAR(50) NOT NULL, 
            target_word VARCHAR(50) NOT NULL,
            other_word_1 VARCHAR(50) NOT NULL,
            other_word_2 VARCHAR(50) NOT NULL,
            other_word_3 VARCHAR(50) NOT NULL,
            user_id BIGINT,  
            added_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT unique_word_per_user UNIQUE (russian_word, user_id)
            );
        """)
 
        # Связующая таблица (для слов в изучении)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_word(
            user_id BIGINT NOT NULL,
            words_id INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (user_id, words_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (words_id) REFERENCES words(id) ON DELETE CASCADE
            );
        """)
 
        # Таблица удаленных слов (для сохранения прогресса)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deleted_words(
            user_id BIGINT NOT NULL,
            words_id INTEGER NOT NULL,
            deleted_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (user_id, words_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (words_id) REFERENCES words(id) ON DELETE CASCADE
            );
        """)
 
        # Таблица для хранения истории
        cur.execute("""
            CREATE TABLE IF NOT EXISTS learned_words(
            user_id BIGINT NOT NULL,
            words_id INTEGER NOT NULL,
            learned_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (user_id, words_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (words_id) REFERENCES words(id) ON DELETE CASCADE
            );
        """)
 
        # Индексы для ускорения запросов
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_word_user_id ON user_word(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_deleted_words_user_id ON deleted_words(user_id);")
 
        # Добавляем начальный набор слов, в последствии этот момент можно доработать, чтобы слова подгружались из CSV или JSON фалов
        initial_words = [
            ('Кот', 'Cat', 'Dog', 'White', 'Tree'),
            ('Собака', 'Dog', 'Green', 'Animal', 'Table'),
            ('Дом', 'House', 'Building', 'Home', 'Roof'),
            ('Солнце', 'Sun', 'Star', 'Light', 'Sky'),
            ('Вода', 'Water', 'Liquid', 'Ocean', 'Rain'),
            ('Огонь', 'Fire', 'Flame', 'Heat', 'Burn'),
            ('Земля', 'Earth', 'Ground', 'Soil', 'World'),
            ('Воздух', 'Air', 'Wind', 'Breeze', 'Atmosphere'),
            ('Дерево', 'Tree', 'Wood', 'Forest', 'Leaf'),
            ('Цветок', 'Flower', 'Rose', 'Plant', 'Bloom'),
            ('Книга', 'Book', 'Page', 'Read', 'Library'),
            ('Ручка', 'Pen', 'Pencil', 'Write', 'Ink'),
            ('Стол', 'Table', 'Desk', 'Wooden', 'Chair'),
            ('Стул', 'Chair', 'Seat', 'Furniture', 'Bench'),
            ('Окно', 'Window', 'Glass', 'View', 'Open'),
            ('Дверь', 'Door', 'Entrance', 'Exit', 'Handle'),
            ('Город', 'City', 'Town', 'Urban', 'Street'),
            ('Деревня', 'Village', 'Country', 'Rural', 'Farm'),
            ('Машина', 'Car', 'Vehicle', 'Drive', 'Road'),
            ('Поезд', 'Train', 'Railway', 'Station', 'Track'),
            ('Самолет', 'Airplane', 'Fly', 'Airport', 'Wings'),
            ('Корабль', 'Ship', 'Boat', 'Sail', 'Ocean'),
            ('Деньги', 'Money', 'Cash', 'Currency', 'Wealth'),
            ('Работа', 'Work', 'Job', 'Office', 'Career'),
            ('Школа', 'School', 'Education', 'Learn', 'Teacher'),
            ('Университет', 'University', 'College', 'Study', 'Degree'),
            ('Больница', 'Hospital', 'Doctor', 'Medicine', 'Health'),
            ('Парк', 'Park', 'Garden', 'Walk', 'Nature'),
            ('Река', 'River', 'Stream', 'Water', 'Flow'),
            ('Гора', 'Mountain', 'Peak', 'Climb', 'Hill'),
            ('Лес', 'Forest', 'Woods', 'Trees', 'Wild'),
            ('Море', 'Sea', 'Ocean', 'Beach', 'Wave'),
            ('Озеро', 'Lake', 'Pond', 'Water', 'Fish'),
            ('Птица', 'Bird', 'Fly', 'Wings', 'Feather'),
            ('Рыба', 'Fish', 'Swim', 'Water', 'Ocean'),
            ('Змея', 'Snake', 'Reptile', 'Slither', 'Venom'),
            ('Лошадь', 'Horse', 'Animal', 'Ride', 'Gallop'),
            ('Корова', 'Cow', 'Farm', 'Milk', 'Animal'),
            ('Овца', 'Sheep', 'Wool', 'Farm', 'Animal'),
            ('Свинья', 'Pig', 'Farm', 'Pork', 'Animal'),
            ('Курица', 'Chicken', 'Bird', 'Farm', 'Egg'),
            ('Хлеб', 'Bread', 'Bakery', 'Wheat', 'Loaf'),
            ('Молоко', 'Milk', 'Dairy', 'Cow', 'White'),
            ('Сыр', 'Cheese', 'Dairy', 'Milk', 'Yellow'),
            ('Мясо', 'Meat', 'Beef', 'Chicken', 'Pork'),
            ('Фрукт', 'Fruit', 'Apple', 'Banana', 'Orange'),
            ('Овощ', 'Vegetable', 'Carrot', 'Potato', 'Tomato'),
            ('Яблоко', 'Apple', 'Fruit', 'Red', 'Tree'),
            ('Банан', 'Banana', 'Fruit', 'Yellow', 'Peel'),
            ('Апельсин', 'Orange', 'Fruit', 'Citrus', 'Juice')
        ]
 
        for word in initial_words:
            try:
                cur.execute("""
                    INSERT INTO words (russian_word, target_word, other_word_1, other_word_2, other_word_3)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (russian_word) DO NOTHING;
                """, word)
            except errors.UniqueViolation:
                conn.rollback()
 
        conn.commit()
    conn.close()
 
def add_user_if_not_exists(user_id: int, username: str):
    """
    Функция добавляет пользователя и связывает его только с новыми словами
    """
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        # Добавляем/обновляем пользователя, если у него например изменилось имя
        cur.execute("""
            INSERT INTO users (id, name)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name,
                last_active = NOW();
        """, (user_id, username))
 
        # Добавляем только новые слова, которые пользователь еще не удалял (для новых добавляется вся база)
        cur.execute("""
            INSERT INTO user_word (user_id, words_id)
            SELECT %s, w.id
            FROM words w
            WHERE NOT EXISTS (
                SELECT 1 FROM user_word uw 
                WHERE uw.user_id = %s AND uw.words_id = w.id
            )
            AND NOT EXISTS (
                SELECT 1 FROM deleted_words dw
                WHERE dw.user_id = %s AND dw.words_id = w.id
            )
            AND w.added_at > COALESCE(
                (SELECT MAX(uw.added_at) FROM user_word uw WHERE uw.user_id = %s),
                '1970-01-01'::timestamp
            )
        """, (user_id, user_id, user_id, user_id))
        
        conn.commit()
    conn.close()


def get_random_user_word(user_id: int):
    """
    Возвращает случайное слово для пользователя:
    - либо из его личных слов,
    - либо из общих (user_id IS NULL), если он их не удалял.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT w.id, w.russian_word, w.target_word, 
                   w.other_word_1, w.other_word_2, w.other_word_3
            FROM words w
            JOIN user_word uw ON w.id = uw.words_id
            WHERE uw.user_id = %s
            AND (uw.user_id = %s OR uw.user_id IS NULL)
            AND NOT EXISTS (  
                SELECT 1 FROM deleted_words dw 
                WHERE dw.user_id = %s AND dw.words_id = w.id
            )
            ORDER BY RANDOM()
            LIMIT 1;
        """, (user_id, user_id, user_id))
        return cur.fetchone()
    conn.close()

 
def remove_user_word(user_id: int, word_id: int):
    """
    Функция удаляет связь между пользователем и словом
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Удаляем связь пользователь-слово
            cur.execute("""
                DELETE FROM user_word
                WHERE user_id = %s AND words_id = %s
            """, (user_id, word_id))
            
            # Добавляем запись в deleted_words
            cur.execute("""
                INSERT INTO deleted_words (user_id, words_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, words_id) DO NOTHING;
            """, (user_id, word_id))
            
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при удалении слова: {e}")
        return False
    finally:
        conn.close()


def add_custom_word(user_id: int, russian: str, target: str, wrong1: str, wrong2: str, wrong3: str):
    """
    Добавляет слово, которое будет доступно только этому пользователю.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        try:
            # Пытаемся добавить слово с привязкой к пользователю
            cur.execute("""
                INSERT INTO words (russian_word, target_word, other_word_1, other_word_2, other_word_3, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (russian_word, user_id) DO NOTHING
                RETURNING id;
            """, (russian, target, wrong1, wrong2, wrong3, user_id))
            
            word_id = cur.fetchone()
            if not word_id:  # Если слово уже есть у этого пользователя
                conn.rollback()
                return False
            
            # Связываем слово с пользователем (добавляем в user_word)
            cur.execute("""
                INSERT INTO user_word (user_id, words_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, words_id) DO NOTHING;
            """, (user_id, word_id[0]))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Ошибка при добавлении слова: {e}")
            return False
    conn.close()


def get_word_by_id(word_id):
    """
    Функция получает слово по его ID
    """
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, russian_word, target_word, 
                   other_word_1, other_word_2, other_word_3
            FROM words
            WHERE id = %s
        """, (word_id,))
        return cur.fetchone()
    conn.close()