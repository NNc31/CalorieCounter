import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
import os

class Database:
    def __init__(self):
        self.connection = psycopg2.connect(
            dbname=os.getenv('PGDATABASE'),
            user=os.getenv('PGUSER'),
            password=os.getenv('PGPASSWORD'),
            host=os.getenv('PGHOST'),
            port=os.getenv('PGPORT')
        )
        self.connection.autocommit = True

    def create_tables(self):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS dishes (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id),
                    name VARCHAR(255) UNIQUE NOT NULL,
                    calories INT NOT NULL,
                    protein REAL,
                    fat REAL,
                    carbs REAL,
                    is_active BOOLEAN DEFAULT TRUE
                );
                
                CREATE TABLE IF NOT EXISTS daily_intake (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id),
                    dish_id INT REFERENCES dishes(id),
                    date DATE DEFAULT CURRENT_DATE,
                    grams REAL
);
            """)

    def add_user(self, telegram_id):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (telegram_id)
                VALUES (%s)
                ON CONFLICT (telegram_id) DO NOTHING;
            """, (telegram_id,))
                
    def add_dish(self, telegram_id, name, calories, protein, fat, carbs):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name
                FROM dishes
                WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)
                AND name = %s;
            """, (telegram_id, name))
            existing_dish = cursor.fetchone()
            if existing_dish:
                timestamp = datetime.now().strftime("%d.%m.%y %H:%M")
                new_name = f"{existing_dish[1]} ({timestamp})"
                cursor.execute("""
                    UPDATE dishes
                    SET name = %s, is_active = FALSE
                    WHERE id = %s;
                """, (new_name, existing_dish[0]))
            cursor.execute("""
                INSERT INTO dishes (user_id, name, calories, protein, fat, carbs, is_active)
                VALUES (
                    (SELECT id FROM users WHERE telegram_id = %s),
                    %s, %s, %s, %s, %s, TRUE
                );
            """, (telegram_id, name, calories, protein, fat, carbs))

    def get_daily_summary(self, telegram_id):
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    SUM(calories * grams / 100) AS total_calories,
                    SUM(protein * grams / 100) AS total_protein,
                    SUM(fat * grams / 100) AS total_fat,
                    SUM(carbs * grams / 100) AS total_carbs,
                    STRING_AGG(name, ', ') AS consumed_dishes
                FROM dishes d
                INNER JOIN daily_intake di ON d.id = di.dish_id AND d.user_id = di.user_id
                WHERE d.user_id = (SELECT id FROM users WHERE telegram_id = %s)
                  AND di.date = %s;
            """, (telegram_id, date.today()))
            return cursor.fetchone()

    def reset_daily_data(self, telegram_id):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM daily_intake
                WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)
                  AND date = %s;
            """, (telegram_id, date.today()))
    def get_dish_by_name(self, telegram_id, name):
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, name
                FROM dishes
                WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)
                AND name = %s
                LIMIT 1;
            """, (telegram_id, name))
            return cursor.fetchone()

    def add_consumed_dish(self, telegram_id, name, grams):
        dish = self.get_dish_by_name(telegram_id, name)
        if dish:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO daily_intake (user_id, dish_id, date, grams)
                    VALUES (
                        (SELECT id FROM users WHERE telegram_id = %s),
                        %s, CURRENT_DATE, %s
                    );
                """, (telegram_id, dish['id'], grams))
            return True
        return False
        
    def remove_dish(self, telegram_id, name):
        dish = self.get_dish_by_name(telegram_id, name)
        if dish:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE dishes
                    SET is_active = FALSE
                    WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)
                    AND name = %s;
                """, (telegram_id, name))
            return True
        return False
        
    def get_menu(self, telegram_id):
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT STRING_AGG(name, ', ') AS menu_values
                FROM dishes
                WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s) AND is_active = TRUE
            """, (telegram_id,))
            return cursor.fetchone()

    def get_history_summary(self, telegram_id, historyDate):
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    SUM(calories * grams / 100) AS total_calories,
                    SUM(protein * grams / 100) AS total_protein,
                    SUM(fat * grams / 100) AS total_fat,
                    SUM(carbs * grams / 100) AS total_carbs,
                    STRING_AGG(name, ', ') AS consumed_dishes
                FROM dishes d
                INNER JOIN daily_intake di ON d.id = di.dish_id AND d.user_id = di.user_id
                WHERE d.user_id = (SELECT id FROM users WHERE telegram_id = %s)
                  AND di.date = %s;
            """, (telegram_id, historyDate))
            return cursor.fetchone()