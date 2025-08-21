import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

def change_admin_password():

    db_path = "data/data.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, username, password_hash FROM admin_credentials")
        admins = cursor.fetchall()
        
        if not admins:
            return False
        

        for admin_id, username, password_hash in admins:
            print(f"   ID: {admin_id}, Username: {username}")
            print(f"   Поточний хеш: {password_hash[:20]}...")
        
        admin_id = input("\n🔑 Введіть ID адміністратора для зміни пароля: ").strip()
        
        if not admin_id.isdigit():
            print("❌ ID має бути числом")
            return False
        
        admin_id = int(admin_id)
        
        cursor.execute("SELECT username FROM admin_credentials WHERE id = ?", (admin_id,))
        admin = cursor.fetchone()
        
        if not admin:
            print(f"❌ Адміністратор з ID {admin_id} не знайдений")
            return False
        
        print(f"✅ Знайдено адміністратора: {admin[0]}")
        
        new_password = input("🔐 Введіть новий пароль: ").strip()
        
        if not new_password:
            print("❌ Пароль не може бути порожнім")
            return False
        
        new_password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        
        print(f"🔐 Новий хеш: {new_password_hash[:20]}...")
        
        cursor.execute("UPDATE admin_credentials SET password_hash = ? WHERE id = ?", (new_password_hash, admin_id))
        conn.commit()
        
        print(f"✅ Пароль для адміністратора {admin[0]} (ID: {admin_id}) успішно змінено!")
        
        cursor.execute("SELECT password_hash FROM admin_credentials WHERE id = ?", (admin_id,))
        stored_hash = cursor.fetchone()[0]
        
        if check_password_hash(stored_hash, new_password):
            print("✅ Перевірка пароля пройшла успішно!")
        else:
            print("❌ Помилка: пароль не перевіряється!")
        
        return True
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_password():
    
    db_path = "data/data.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, username, password_hash FROM admin_credentials")
        admins = cursor.fetchall()
        
        if not admins:
            print("❌ Адміністратори не знайдені")
            return False
        
        print("👥 Поточні адміністратори:")
        for admin_id, username, password_hash in admins:
            print(f"   ID: {admin_id}, Username: {username}")
            print(f"   Хеш: {password_hash}")
        
        test_password = input("\n🔐 Введіть пароль для тестування: ").strip()
        
        if not test_password:
            print("❌ Пароль не може бути порожнім")
            return False
        
        for admin_id, username, password_hash in admins:
            if check_password_hash(password_hash, test_password):
                print(f"✅ Пароль підходить для адміністратора {username} (ID: {admin_id})")
                return True
            else:
                print(f"❌ Пароль не підходить для адміністратора {username} (ID: {admin_id})")
        
        print("❌ Пароль не підходить жодному адміністратору")
        return False
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
                    
    print("🔐 Управління паролями адміністраторів")
    print("=" * 70)
    
    while True:
        print("\n📋 Виберіть дію:")
        print("1. 🔑 Змінити пароль адміністратора")
        print("2. 🧪 Тестувати поточний пароль")
        print("3. 🚪 Вийти")
        
        choice = input("\n👉 Ваш вибір (1-3): ").strip()
        
        if choice == "1":
            change_admin_password()
        elif choice == "2":
            test_password()
        elif choice == "3":
            print("👋 До побачення!")
            break
        else:
            print("❌ Невірний вибір. Спробуйте ще раз.")
        
        input("\nНатисніть Enter для продовження...")

if __name__ == "__main__":
    main()
