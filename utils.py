import mysql.connector
from mysql.connector import pooling
import json
from consultas import consultas
from dotenv import load_dotenv
import os

load_dotenv()  # Carga variables del archivo .env

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


class MySQLSingleton:
    _instance = None

    def __new__(cls, host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, pool_size=5):
        if cls._instance is None:
            try:
                cls._instance = super(MySQLSingleton, cls).__new__(cls)

                # Crear un pool de conexiones
                cls._instance.connection_pool = pooling.MySQLConnectionPool(
                    pool_name="mypool",
                    pool_size=pool_size,
                    host=host,
                    user=user,
                    password=password,
                    database=database
                )

                print("✅ Pool de conexiones MySQL creado correctamente.")
            except mysql.connector.Error as e:
                print(f"❌ Error al crear el pool de conexiones: {e}")
                cls._instance = None
        return cls._instance

    def get_connection(self):
        """ Obtiene una conexión del pool """
        try:
            return self.connection_pool.get_connection()
        except mysql.connector.Error as e:
            print(f"❌ Error al obtener conexión: {e}")
            return None

    def close_connection(self, conn, cursor):
        """ Cierra el cursor y devuelve la conexión al pool """
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def ejecutar_query(query):
    """
    Ejecuta una consulta SQL y devuelve los resultados en formato de lista de diccionarios.
    """
    db = MySQLSingleton()
    conn = db.get_connection()

    if conn is None:
        return {"error": "No se pudo obtener una conexión"}

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(query)
        resultados = cursor.fetchall()
        return resultados
    except mysql.connector.Error as e:
        print(f"❌ Error ejecutando query: {e}")
        return {"error": str(e)}
    finally:
        db.close_connection(conn, cursor)


def extraer_data():
    # Guardar los resultados en un diccionario
    resultados_json = {nombre: ejecutar_query(
        query) for nombre, query in consultas.items()}

    # Guardar en un archivo JSON
    if resultados_json:
        with open("resultados.json", "w", encoding="utf-8") as f:
            json.dump(resultados_json, f, indent=4, ensure_ascii=False)
        print("📂 Resultados guardados en 'resultados.json'")


if __name__ == "__main__":
    # extraer_data()
    pass
