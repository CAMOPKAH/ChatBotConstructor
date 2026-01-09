from database.base import SessionLocal, engine, Base
from database.models import Block, UserSession, UserParam, Module
import os

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear existing data
    db.query(UserSession).delete()
    db.query(UserParam).delete()
    db.query(Block).delete()
    db.query(Module).delete()
    db.commit()

    # --- MODULES ---
    # Assuming running from chatbot/ directory
    giga_path = os.path.abspath("MOD/GigaAI/giga_ai.py")
    
    giga_module = Module(
        name="GigaAI",
        py_file=giga_path,
        status="stop"
    )
    db.add(giga_module)

    # --- MENUS ---
    MAIN_MENU = ["Собрать данные", "Расчёт калорий", "Вывести всю информацию", "AI Ассистент"]
    GENDER_MENU = ["Мужской", "Женский"]
    EXIT_MENU = ["Выход в меню"]

    # --- SCRIPTS ---

    # Block 1: Main Menu
    script_1 = f"""
if event == 'enter':
    send_message("Главное меню. Выберите действие:", {MAIN_MENU})
elif event == 'message':
    if input_text == 'Собрать данные':
        go_to(10)
    elif input_text == 'Расчёт калорий':
        go_to(20)
    elif input_text == 'Вывести всю информацию':
        go_to(30)
    elif input_text == 'AI Ассистент':
        go_to(40)
    else:
        send_message("Пожалуйста, выберите пункт из меню.", {MAIN_MENU})
"""

    # --- COLLECTION FLOW (10-15) ---
    # ... (Same as before)
    script_10 = """
if event == 'enter':
    send_message("Введите ваше ФИО:")
elif event == 'message':
    set_param('fio', input_text)
    go_to(11)
"""
    script_11 = """
if event == 'enter':
    send_message("Введите ваш возраст (полных лет):")
elif event == 'message':
    if not input_text.isdigit():
        send_message("Пожалуйста, введите число.")
    else:
        set_param('age', input_text)
        go_to(12)
"""
    script_12 = f"""
if event == 'enter':
    send_message("Выберите ваш пол:", {GENDER_MENU})
elif event == 'message':
    if input_text in {GENDER_MENU}:
        set_param('gender', input_text)
        go_to(13)
    else:
        send_message("Пожалуйста, выберите пол кнопкой.", {GENDER_MENU})
"""
    script_13 = """
if event == 'enter':
    send_message("Введите ваш рост (см):")
elif event == 'message':
    if not input_text.isdigit():
        send_message("Пожалуйста, введите число.")
    else:
        set_param('height', input_text)
        go_to(14)
"""
    script_14 = f"""
if event == 'enter':
    send_message("Введите ваш вес (кг):")
elif event == 'message':
    if not input_text.isdigit():
        send_message("Пожалуйста, введите число.")
    else:
        set_param('weight', input_text)
        send_message("Данные сохранены!", {MAIN_MENU})
        go_to(1)
"""

    # --- CALCULATION (20) ---
    script_20 = f"""
if event == 'enter':
    age = get_param('age')
    gender = get_param('gender')
    height = get_param('height')
    weight = get_param('weight')

    if not (age and gender and height and weight):
        send_message("Недостаточно данных. Пожалуйста, заполните анкету.", {MAIN_MENU})
        go_to(1)
    else:
        w = float(weight)
        h = float(height)
        a = int(age)
        
        if gender == 'Мужской':
            bmr = 88.36 + (13.4 * w) + (4.8 * h) - (5.7 * a)
        else:
            bmr = 447.6 + (9.2 * w) + (3.1 * h) - (4.3 * a)
            
        send_message(f"Ваш базовый обмен веществ (BMR): {{bmr:.2f}} ккал/день.", {MAIN_MENU})
        go_to(1)
"""

    # --- SHOW INFO (30) ---
    script_30 = f"""
if event == 'enter':
    fio = get_param('fio') or "Не указано"
    age = get_param('age') or "Не указано"
    gender = get_param('gender') or "Не указано"
    height = get_param('height') or "Не указано"
    weight = get_param('weight') or "Не указано"
    
    msg = f"Ваши данные:\\nФИО: {{fio}}\\nВозраст: {{age}}\\nПол: {{gender}}\\nРост: {{height}}\\nВес: {{weight}}"
    send_message(msg, {MAIN_MENU})
    go_to(1)
"""

    # --- AI ASSISTANT (40) ---
    script_40 = f"""
if event == 'enter':
    # Initialize module
    ModuleStart('GigaAI')
    send_message("Привет! Я Доктор Абсолюткин. Спрашивай меня о ЗОЖ.", {EXIT_MENU})
elif event == 'message':
    if input_text == 'Выход в меню':
        go_to(1)
    else:
        send_message("Думаю...")
        # Call module function
        # We assume call_module returns the answer synchronously or we handle it
        answer = call_module('GigaAI', 'ask', input_text)
        send_message(answer, {EXIT_MENU})
"""

    blocks = [
        Block(id=1, name="MainMenu", script_code=script_1, is_start=True),
        
        Block(id=10, name="AskFIO", script_code=script_10, is_start=False),
        Block(id=11, name="AskAge", script_code=script_11, is_start=False),
        Block(id=12, name="AskGender", script_code=script_12, is_start=False),
        Block(id=13, name="AskHeight", script_code=script_13, is_start=False),
        Block(id=14, name="AskWeight", script_code=script_14, is_start=False),
        
        Block(id=20, name="Calc", script_code=script_20, is_start=False),
        Block(id=30, name="ShowInfo", script_code=script_30, is_start=False),
        
        Block(id=40, name="AI_Chat", script_code=script_40, is_start=False),
    ]

    for b in blocks:
        db.add(b)
    
    db.commit()
    print("Database seeded successfully with Modules and AI flow.")
    db.close()

if __name__ == "__main__":
    seed()
