from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import json
from database.settings_db import (
    get_all_settings, save_start_message_config, save_our_chat_config, save_channel_join_config, 
    get_channel_invite_links, add_channel_invite_link, update_channel_invite_link, delete_channel_invite_link,
    get_subscription_message, update_admin_password, save_channel_leave_config,
    get_welcome_without_subscription, save_welcome_without_subscription, save_subscription_message_with_buttons,
    get_captcha_config, get_captcha_settings, save_captcha_settings,
    get_answers_config, save_answers_config, get_private_lesson_config, save_private_lesson_config,
    get_tariffs_config, save_tariffs_config, get_clothes_tariff_config, save_clothes_tariff_config,
    get_tech_tariff_config, save_tech_tariff_config, get_clothes_payment_config, save_clothes_payment_config,
    get_tech_payment_config, save_tech_payment_config
)
from database.client_db import (
    get_users_count, get_users_with_statuses, admin_update_user_status,
    get_subscription_stats, admin_delete_user,
    get_analytics_counts, get_analytics_timeseries, get_param_distribution, get_status_distribution,
    get_start_params_stats
)
from database.start_params_db import add_start_param, delete_start_param, get_total_start_params, get_users_with_start_params, get_start_params_stats
from config import token
from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.security import generate_password_hash
from database.settings_db import check_password
from aiogram import Bot

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Функция для получения отображения этапа с ID
def get_stage_id_display(stage_name):
    stage_map = {
        'Нажал старт': '1 - Нажал старт',
        'Прошел капчу': '2 - Прошел капчу',
        'Посмотрел ответы': '3 - Посмотрел ответы',
        'Посмотрел приватный урок': '4 - Посмотрел приватный урок',
        'Посмотрел тарифы': '5 - Посмотрел тарифы',
        'Посмотрел тарифы одежда': '6 - Посмотрел тарифы одежда',
        'Посмотрел тарифы техника': '7 - Посмотрел тарифы техника',
        'Нажал оплатить техника': '8 - Нажал оплатить техника',
        'Нажал оплатить одежда': '9 - Нажал оплатить одежда',
        'Оплатил одежду': '10 - Оплатил одежду',
        'Оплатил технику': '11 - Оплатил технику'
    }
    return stage_map.get(stage_name, stage_name)

@app.template_filter('from_json')
def from_json_filter(value):
    if value and isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    elif isinstance(value, list):
        return value
    return []


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


ADMIN_USERNAME = "Woldemar"

def load_settings():
    return get_all_settings()

@app.route('/')
@login_required
def admin_panel():
    print("DEBUG: admin_panel route called")
    return render_template('admin_panel.html')

@app.route('/welcome-settings')
@login_required
def welcome_settings():
    settings = load_settings()
    welcome_without_subscription = get_welcome_without_subscription()
    return render_template('welcome_settings.html', 
                         settings=settings, 
                         welcome_without_subscription=welcome_without_subscription)


@app.route('/channel-join-settings')
@login_required
def channel_join_settings():
    settings = load_settings()
    invite_links_raw = get_channel_invite_links()
    
    # Преобразуем кортежи в словари для удобства работы
    invite_links = []
    for link_tuple in invite_links_raw:
        link_dict = {
            'id': link_tuple[0],
            'invite_link': link_tuple[1],
            'channel_name': link_tuple[2],
            'message_text': link_tuple[3],
            'media_type': link_tuple[4],
            'media_url': link_tuple[5],
            'is_active': link_tuple[6]
        }
        # Получаем настройки капчи для каждого посилання
        link_dict['captcha_config'] = get_captcha_config(link_dict['id'])
        invite_links.append(link_dict)
    
    return render_template('channel_join_settings.html', settings=settings, invite_links=invite_links)

@app.route('/channel-leave-settings')
@login_required
def channel_leave_settings():
    settings = load_settings()
    return render_template('channel_leave_settings.html', settings=settings)


@app.route('/captcha-settings')
@login_required
def captcha_settings():
    """Страница настройки глобальной капчи"""
    captcha_settings = get_captcha_settings()
    return render_template('captcha_settings.html', captcha_settings=captcha_settings)


@app.route('/answers-settings')
@login_required
def answers_settings():
    """Страница настройки сообщения 'Ответы на вопросы'"""
    answers_config = get_answers_config()
    return render_template('answers_settings.html', answers_config=answers_config)


@app.route('/private-lesson-settings')
@login_required
def private_lesson_settings():
    """Страница настройки сообщения 'Приватный урок'"""
    private_lesson_config = get_private_lesson_config()
    return render_template('private_lesson_settings.html', private_lesson_config=private_lesson_config)


@app.route('/tariffs-settings')
@login_required
def tariffs_settings():
    """Страница настройки сообщения 'Посмотреть тарифы'"""
    from database.settings_db import get_tariff_selection_buttons_config
    
    tariffs_config = get_tariffs_config()
    clothes_config = get_clothes_tariff_config()
    tech_config = get_tech_tariff_config()
    selection_buttons_config = get_tariff_selection_buttons_config()
    
    # Об'єднуємо всі налаштування
    combined_config = {
        **tariffs_config,
        'clothes_button_text': selection_buttons_config.get('clothes_selection_button_text'),
        'tech_button_text': selection_buttons_config.get('tech_selection_button_text')
    }
    
    return render_template('tariffs_settings.html', 
                         tariffs_config=combined_config,
                         clothes_config=clothes_config,
                         tech_config=tech_config)




@app.route('/users')
@login_required
def users_list():
    page = request.args.get('page', 1, type=int)
    per_page = 100
    
    users, total_users, total_pages, current_page, per_page = get_users_with_statuses(page, per_page)
    
    # Получаем статистику по подпискам
    subscription_stats = get_subscription_stats()
    
    return render_template('users.html', 
                         users=users, 
                         current_page=current_page, 
                         total_pages=total_pages, 
                         total_users=total_users,
                         per_page=per_page,
                         subscription_stats=subscription_stats,
                         get_stage_id_display=get_stage_id_display)


@app.route('/analytics')
@login_required
def analytics_dashboard():
    """CRM mini-dashboard: overall by tags, payment funnel, time filters."""
    from datetime import datetime, timedelta
    # Defaults: last 30 days
    end_date = request.args.get('end_date')
    start_date = request.args.get('start_date')
    param = request.args.get('param')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=29)).strftime('%Y-%m-%d')

    counts = get_analytics_counts(start_date, end_date, param)
    timeseries = get_analytics_timeseries(start_date, end_date, param)
    param_dist = get_param_distribution(start_date, end_date, param)
    status_dist = get_status_distribution(start_date, end_date, param)
    # Get all available start params for dropdown
    all_start_params = get_start_params_stats()

    return render_template(
        'analytics.html',
        counts=counts,
        timeseries=timeseries,
        param_dist=param_dist,
        status_dist=status_dist,
        all_start_params=all_start_params,
        start_date=start_date,
        end_date=end_date,
        selected_param=param
    )

@app.route('/start-params', methods=['GET', 'POST'])
@login_required
def start_params():
    if request.method == 'POST':
        param_name = request.form.get('param_name')
        description = request.form.get('description')
        
        # Валидация
        if not param_name:
            return render_template('start_params.html', 
                                message="Ошибка: название параметра обязательно", 
                                message_type="danger")
        
        # Добавление параметра
        success = add_start_param(param_name, description)
        
        if success:
            flash(f"✅ Стартовый параметр '{param_name}' успешно создан/обновлен", 'success')
            return redirect(url_for('start_params'))
        else:
            flash("❌ Ошибка при создании стартового параметра", 'error')
            return redirect(url_for('start_params'))
    
    # GET запит - показуємо форму
    total_params = get_total_start_params()
    total_users_with_params = get_users_with_start_params()
    total_users = get_users_count()
    
    # Отримуємо статистику по параметрах
    start_params_stats = get_start_params_stats()
    start_params_data = []
    
    for param_name, user_count in start_params_stats:
        start_params_data.append({
            'param_name': param_name,
            'user_count': user_count
        })
    
    print(f"DEBUG: start_params_data: {start_params_data}")
    
    return render_template('start_params.html',
                         total_params=total_params,
                         total_users_with_params=total_users_with_params,
                         total_users=total_users,
                         start_params=start_params_data,
                         bot_username='refandgold1_bot')

@app.route('/delete-start-param/<param_name>', methods=['POST'])
@login_required
def delete_start_param_route(param_name):
    success = delete_start_param(param_name)
    
    if success:
        flash(f"✅ Стартовий параметр '{param_name}' успішно видалено", 'success')
    else:
        flash(f"❌ Помилка при видаленні стартового параметра '{param_name}'", 'danger')
    
    return redirect(url_for('start_params'))


@app.route('/api/start-params-list')
@login_required
def get_start_params_list():
    """API endpoint для отримання списку стартових параметрів з кількістю користувачів"""
    try:
        from database.start_params_db import get_start_params_stats
        
        start_params_stats = get_start_params_stats()
        start_params_data = []
        
        for param_name, user_count in start_params_stats:
            start_params_data.append({
                'param_name': param_name,
                'user_count': user_count
            })
        
        return jsonify(start_params_data)
        
    except Exception as e:
        print(f"ERROR in get_start_params_list: {e}")
        return jsonify([]), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    print(f"DEBUG: login route called with method: {request.method}")
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and check_password(password):
            user = User(username)
            login_user(user)
            print(f"DEBUG: successful login for user: {username}")
            flash('Успешная авторизация!', 'success')
            return redirect(url_for('admin_panel'))
        else:
            print(f"DEBUG: failed login attempt for username: {username}")
            flash('Неверный логин или пароль!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    print("DEBUG: logout route called")
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/edit_start_message', methods=['POST'])
@login_required
def edit_start_message():
    print("DEBUG: edit_start_message route called")
    print(f"DEBUG: form data: {request.form}")
    new_message = request.form['start_message']
    media_type = request.form['media_type']
    media_url = request.form['media_url']
    answers_button_text = request.form.get('answers_button_text', '💡 Ответы')
    our_chat_button_text = request.form.get('our_chat_button_text', '🎓 Приватный урок')
    shop_button_text = request.form.get('shop_button_text', '💰 Тарифы')
    inline_buttons_position = request.form.get('inline_buttons_position', 'below')
    
    if not new_message.strip():
        flash('Сообщение не может быть пустым!', 'error')
        return redirect(url_for('welcome_settings'))
    
    if media_type != "none" and not media_url.strip():
        flash('URL медиа не может быть пустым при выборе типа медиа!', 'error')
        return redirect(url_for('welcome_settings'))
    
    # Обробка інлайн кнопок
    button_texts = request.form.getlist('button_text[]')
    button_links = request.form.getlist('button_link[]')
    
    inline_buttons = []
    for i in range(len(button_texts)):
        if button_texts[i].strip() and button_links[i].strip():
            # Обмежуємо довжину тексту та URL
            text = button_texts[i].strip()[:64]  # Максимум 64 символи для тексту кнопки
            url = button_links[i].strip()[:2048]  # Максимум 2048 символів для URL
            
            inline_buttons.append({
                'text': text,
                'url': url
            })
    
    # Обмежуємо кількість кнопок до 8 (максимум для Telegram)
    if len(inline_buttons) > 8:
        inline_buttons = inline_buttons[:8]
        flash('Додано тільки перші 8 кнопок (обмеження Telegram)', 'error')
    
    config = {
        "message": new_message.strip(),
        "media_type": media_type,
        "media_url": media_url.strip(),
        "inline_buttons": inline_buttons,
        "inline_buttons_position": inline_buttons_position,
        "answers_button_text": answers_button_text.strip(),
        "our_chat_button_text": our_chat_button_text.strip(),
        "shop_button_text": shop_button_text.strip()
    }
    
    print(f"DEBUG: saving start message config: {config}")
    save_start_message_config(config)
    print("DEBUG: start message config saved successfully")
    flash('Стартовое сообщение обновлено!', 'success')
    
    return redirect(url_for('welcome_settings'))


@app.route('/save_welcome_without_subscription_route', methods=['POST'])
@login_required
def save_welcome_without_subscription_route():
    """Збереження привітального повідомлення без підписки"""
    try:
        message_text = request.form.get('message_text', '').strip()
        media_type = request.form.get('media_type', 'none')
        media_url = request.form.get('media_url', '').strip()
        channel_url = request.form.get('channel_url', '').strip()
        channel_id = request.form.get('channel_id', '').strip()
        channel_button_text = request.form.get('channel_button_text', '📢 Подписаться на канал').strip()
        
        if not message_text:
            flash('Текст повідомлення не може бути порожнім!', 'error')
            return redirect(url_for('welcome_settings'))
        
        if not channel_url:
            flash('Посилання на канал не може бути порожнім!', 'error')
            return redirect(url_for('welcome_settings'))
        
        if not channel_id:
            flash('ID каналу не може бути порожнім!', 'error')
            return redirect(url_for('welcome_settings'))
        
        if media_type != "none" and not media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('welcome_settings'))
        
        # Зберігаємо налаштування
        success = save_welcome_without_subscription(
            message_text=message_text,
            media_type=media_type,
            media_url=media_url,
            channel_url=channel_url,
            channel_id=channel_id,
            channel_button_text=channel_button_text
        )
        
        if success:
            flash('Привітальне повідомлення без підписки успішно збережено!', 'success')
        else:
            flash('Помилка при збереженні налаштувань!', 'error')
        
        return redirect(url_for('welcome_settings'))
        
    except Exception as e:
        print(f"ERROR in save_welcome_without_subscription: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('welcome_settings'))


@app.route('/edit_our_chat_message', methods=['POST'])
@login_required
def edit_our_chat_message():
    print("DEBUG: edit_our_chat_message route called")
    print(f"DEBUG: form data: {request.form}")
    new_message = request.form['our_chat_message']
    media_type = request.form['media_type']
    media_url = request.form['media_url']
    subscription_button_text = request.form.get('subscription_button_text', '📢 Подписка')
    subscription_channel_url = request.form.get('subscription_channel_url', 'https://t.me/your_channel')
    check_subscription_button_text = request.form.get('check_subscription_button_text', '✅ Проверить подписку')
    
    if not new_message.strip():
        flash('Сообщение не может быть пустым!', 'error')
        return redirect(url_for('our_chat_settings'))
    
    if media_type != "none" and not media_url.strip():
        flash('URL медиа не может быть пустым при выборе типа медиа!', 'error')
        return redirect(url_for('our_chat_settings'))
    
    if not subscription_channel_url.strip():
        flash('URL канала для подписки не может быть пустым!', 'error')
        return redirect(url_for('our_chat_settings'))
    
    config = {
        "message": new_message.strip(),
        "media_type": media_type,
        "media_url": media_url.strip(),
        "subscription_button_text": subscription_button_text.strip(),
        "subscription_channel_url": subscription_channel_url.strip(),
        "check_subscription_button_text": check_subscription_button_text.strip()
    }
    
    print(f"DEBUG: saving our chat config: {config}")
    save_our_chat_config(config)
    print("DEBUG: our chat config saved successfully")
    flash('Сообщение "Наш чат" обновлено!', 'success')
    
    return redirect(url_for('our_chat_settings'))

@app.route('/edit_channel_join_message', methods=['POST'])
@login_required
def edit_channel_join_message():
    print("DEBUG: edit_channel_join_message route called")
    print(f"DEBUG: form data: {request.form}")
    new_message = request.form['channel_join_message']
    media_type = request.form['media_type']
    media_url = request.form['media_url']
    
    if not new_message.strip():
        flash('Сообщение не может быть пустым!', 'error')
        return redirect(url_for('channel_join_settings'))
    
    if media_type != "none" and not media_url.strip():
        flash('URL медиа не может быть пустым при выборе типа медиа!', 'error')
        return redirect(url_for('channel_join_settings'))
    
    config = {
        "message": new_message.strip(),
        "media_type": media_type,
        "media_url": media_url.strip()
    }
    
    print(f"DEBUG: saving channel join config: {config}")
    save_channel_join_config(config)
    print("DEBUG: channel join config saved successfully")
    flash('Сообщение при заявке на вступ до каналу оновлено!', 'success')
    
    return redirect(url_for('channel_join_settings'))

@app.route('/edit_channel_leave_message', methods=['POST'])
@login_required
def edit_channel_leave_message():
    print("DEBUG: edit_channel_leave_message route called")
    print(f"DEBUG: form data: {request.form}")
    new_message = request.form['channel_leave_message']
    media_type = request.form['media_type']
    media_url = request.form['media_url']
    
    if not new_message.strip():
        flash('Сообщение не может быть пустым!', 'error')
        return redirect(url_for('channel_leave_settings'))
    
    if media_type != "none" and not media_url.strip():
        flash('URL медиа не может быть пустым при выборе типа медиа!', 'error')
        return redirect(url_for('channel_leave_settings'))
    
    # Обробка інлайн кнопок
    button_texts = request.form.getlist('button_text[]')
    button_links = request.form.getlist('button_link[]')
    
    inline_buttons = []
    for i in range(len(button_texts)):
        if button_texts[i].strip() and button_links[i].strip():
            # Обмежуємо довжину тексту та URL
            text = button_texts[i].strip()[:64]  # Максимум 64 символи для тексту кнопки
            url = button_links[i].strip()[:2048]  # Максимум 2048 символів для URL
            
            inline_buttons.append({
                'text': text,
                'url': url
            })
    
    # Обмежуємо кількість кнопок до 8 (максимум для Telegram)
    if len(inline_buttons) > 8:
        inline_buttons = inline_buttons[:8]
        flash('Додано тільки перші 8 кнопок (обмеження Telegram)', 'error')
    
    # Налаштування кнопки "Уйти"
    leave_button_text = request.form.get('leave_button_text', 'Уйти').strip()
    leave_message = request.form.get('leave_message', '').strip()
    leave_media_type = request.form.get('leave_media_type', 'none')
    leave_media_url = request.form.get('leave_media_url', '').strip()
    
    if not leave_button_text:
        leave_button_text = 'Уйти'
    
    if leave_media_type != "none" and not leave_media_url:
        flash('URL медиа для кнопки "Уйти" не может быть пустым при выборе типа медиа!', 'error')
        return redirect(url_for('channel_leave_settings'))
    
    # Обробка інлайн кнопок для повідомлення "Уйти"
    leave_button_texts = request.form.getlist('leave_button_text[]')
    leave_button_links = request.form.getlist('leave_button_link[]')
    
    leave_inline_buttons = []
    for i in range(len(leave_button_texts)):
        if leave_button_texts[i].strip() and leave_button_links[i].strip():
            text = leave_button_texts[i].strip()[:64]
            url = leave_button_links[i].strip()[:2048]
            
            leave_inline_buttons.append({
                'text': text,
                'url': url
            })
    
    if len(leave_inline_buttons) > 8:
        leave_inline_buttons = leave_inline_buttons[:8]
        flash('Додано тільки перші 8 кнопок для "Уйти" (обмеження Telegram)', 'error')
    
    # Налаштування кнопки "Возвращаюсь"
    return_button_text = request.form.get('return_button_text', 'Возвращаюсь').strip()
    return_url = request.form.get('return_url', '').strip()
    
    if not return_button_text:
        return_button_text = 'Возвращаюсь'
    
    if not return_url:
        flash('URL для кнопки "Возвращаюсь" не может быть пустым!', 'error')
        return redirect(url_for('channel_leave_settings'))
    
    config = {
        "message": new_message.strip(),
        "media_type": media_type,
        "media_url": media_url.strip(),
        "inline_buttons": inline_buttons,
        "leave_button_text": leave_button_text,
        "leave_message": leave_message,
        "leave_media_type": leave_media_type,
        "leave_media_url": leave_media_url,
        "leave_inline_buttons": leave_inline_buttons,
        "return_button_text": return_button_text,
        "return_url": return_url
    }
    
    print(f"DEBUG: saving channel leave config: {config}")
    save_channel_leave_config(config)
    print("DEBUG: channel leave config saved successfully")
    flash('Сообщение при выходе из канала обновлено!', 'success')
    
    return redirect(url_for('channel_leave_settings'))

@app.route('/add_channel_invite_link', methods=['POST'])
@login_required
def add_channel_invite_link_route():
    print("DEBUG: add_channel_invite_link_route called")
    print(f"DEBUG: form data: {request.form}")
    invite_link = request.form['invite_link'].strip()
    channel_name = request.form['channel_name'].strip()
    message_text = request.form['message_text'].strip()
    media_type = request.form['media_type']
    media_url = request.form['media_url'].strip()
    
    if not invite_link or not channel_name:
        flash('Пригласительная ссылка и название канала обязательны!', 'error')
        return redirect(url_for('channel_join_settings'))
    
    if media_type != "none" and not media_url:
        flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
        return redirect(url_for('channel_join_settings'))
    
    try:
        add_channel_invite_link(invite_link, channel_name, message_text, media_type, media_url)
        print(f"DEBUG: channel invite link added successfully: {invite_link}")
        flash('Запрошувальне посилання успішно додано!', 'success')
    except Exception as e:
        print(f"ERROR in add_channel_invite_link_route: {e}")
        flash(f'Помилка при додаванні: {str(e)}', 'error')
    
    return redirect(url_for('channel_join_settings'))

@app.route('/edit_channel_invite_link/<int:link_id>', methods=['POST'])
@login_required
def edit_channel_invite_link_route(link_id):
    print(f"DEBUG: edit_channel_invite_link_route called with link_id: {link_id}")
    print(f"DEBUG: form data: {request.form}")
    invite_link = request.form['invite_link'].strip()
    channel_name = request.form['channel_name'].strip()
    message_text = request.form['message_text'].strip()
    media_type = request.form['media_type']
    media_url = request.form['media_url'].strip()
    
    if not invite_link or not channel_name:
        flash('Пригласительная ссылка и название канала обязательны!', 'error')
        return redirect(url_for('channel_join_settings'))
    
    if media_type != "none" and not media_url:
        flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
        return redirect(url_for('channel_join_settings'))
    
    try:
        success = update_channel_invite_link(link_id, invite_link, channel_name, message_text, media_type, media_url)
        if success:
            print(f"DEBUG: channel invite link updated successfully for ID: {link_id}")
            flash('Запрошувальне посилання успішно оновлено!', 'success')
        else:
            print(f"DEBUG: failed to update channel invite link for ID: {link_id}")
            flash('Помилка при оновленні!', 'error')
    except Exception as e:
        print(f"ERROR in edit_channel_invite_link_route: {e}")
        flash(f'Помилка при оновленні: {str(e)}', 'error')
    
    return redirect(url_for('channel_join_settings'))

@app.route('/delete_channel_invite_link/<int:link_id>')
@login_required
def delete_channel_invite_link_route(link_id):
    print(f"DEBUG: delete_channel_invite_link_route called with link_id: {link_id}")
    try:
        success = delete_channel_invite_link(link_id)
        if success:
            print(f"DEBUG: channel invite link deleted successfully for ID: {link_id}")
            flash('Запрошувальне посилання успішно видалено!', 'success')
        else:
            print(f"DEBUG: failed to delete channel invite link for ID: {link_id}")
            flash('Помилка при видаленні!', 'error')
    except Exception as e:
        print(f"ERROR in delete_channel_invite_link_route: {e}")
        flash(f'Помилка при видаленні: {str(e)}', 'error')
    
    return redirect(url_for('channel_join_settings'))

@app.route('/start-links')
@login_required
def start_links():
    print("DEBUG: start_links route called")
    from database.settings_db import get_all_start_links
    links = get_all_start_links()
    print(f"DEBUG: start links count: {len(links) if links else 0}")
    return render_template('start_links.html', links=links)

@app.route('/edit-start-link', methods=['POST'])
@login_required
def edit_start_link():
    print("DEBUG: edit_start_link route called")
    print(f"DEBUG: form data: {request.form}")
    from database.settings_db import save_start_link_config
    
    start_param = request.form.get('start_param')
    message_text = request.form.get('message_text')
    media_type = request.form.get('media_type')
    media_url = request.form.get('media_url')
    
    # Парсимо inline кнопки
    button_texts = request.form.getlist('button_text[]')
    button_links = request.form.getlist('button_link[]')
    
    inline_buttons = []
    for i in range(len(button_texts)):
        if button_texts[i].strip() and button_links[i].strip():
            inline_buttons.append({
                'text': button_texts[i].strip(),
                'url': button_links[i].strip()
            })
    
    print(f"DEBUG: saving start link config: start_param={start_param}, message_text={message_text}, media_type={media_type}, media_url={media_url}, inline_buttons={inline_buttons}")
    save_start_link_config(start_param, message_text, media_type, media_url, inline_buttons)
    print("DEBUG: start link config saved successfully")
    
    flash('Ссылка успешно сохранена!', 'success')
    return redirect(url_for('start_links'))

@app.route('/delete-start-link/<int:link_id>')
@login_required
def delete_start_link(link_id):
    print(f"DEBUG: delete_start_link route called with link_id: {link_id}")
    from database.settings_db import delete_start_link
    try:
        delete_start_link(link_id)
        print(f"DEBUG: start link deleted successfully for ID: {link_id}")
        flash('Ссылка удалена!', 'success')
    except Exception as e:
        print(f"ERROR in delete_start_link: {e}")
        flash(f'Помилка при видаленні: {str(e)}', 'error')
    return redirect(url_for('start_links'))

@app.route('/toggle-start-link/<int:link_id>')
@login_required
def toggle_start_link(link_id):
    print(f"DEBUG: toggle_start_link route called with link_id: {link_id}")
    from database.settings_db import toggle_start_link_status, get_all_start_links
    
    links = get_all_start_links()
    current_link = next((link for link in links if link['id'] == link_id), None)
    
    if current_link:
        new_status = not current_link['is_active']
        print(f"DEBUG: toggling start link status from {current_link['is_active']} to {new_status}")
        toggle_start_link_status(link_id, new_status)
        
        status_text = "активирована" if new_status else "деактивирована"
        flash(f'Ссылка {status_text}!', 'success')
    else:
        print(f"DEBUG: start link not found for ID: {link_id}")
        flash('Ссылка не найдена!', 'error')
    
    return redirect(url_for('start_links'))


# Маршрути для роботи з розсилками
@app.route('/mailing-settings')
@login_required
def mailing_settings():
    print("DEBUG: mailing_settings route called")
    from database.settings_db import get_all_mailings
    mailings = get_all_mailings()
    print(f"DEBUG: mailings count: {len(mailings) if mailings else 0}")
    return render_template('mailing_settings.html', mailings=mailings)


@app.route('/create_mailing', methods=['POST'])
@login_required
def create_mailing_route():
    print("DEBUG: create_mailing_route called")
    print(f"DEBUG: form data: {request.form}")
    from database.settings_db import add_mailing
    
    name = request.form['mailing_name'].strip()
    message_text = request.form['message_text'].strip()
    media_type = request.form['media_type']
    media_url = request.form['media_url'].strip() if request.form['media_url'] else None
    
    for key in request.form.keys():
        print(f"   {key}: {request.form[key]}")
    
    # Проверяем, передан ли готовый JSON кнопок
    inline_buttons_json = request.form.get('inline_buttons')
    if inline_buttons_json and inline_buttons_json != 'null':
        try:
            # Проверяем, валидный ли JSON
            json.loads(inline_buttons_json)
            print(f"✅ JSON кнопок валідний, використовуємо його")
        except json.JSONDecodeError:
            print(f"❌ JSON кнопок невалідний, парсимо поля окремо")
            inline_buttons_json = None
    
    # Якщо готовий JSON не передано, парсимо поля окремо
    if not inline_buttons_json or inline_buttons_json == 'null':
        button_texts = request.form.getlist('button_text[]')
        button_links = request.form.getlist('button_link[]')
    
        inline_buttons = []
        for i in range(len(button_texts)):
            text = button_texts[i].strip()
            link = button_links[i].strip()
            print(f"   Кнопка {i+1}: text='{text}', link='{link}'")
            
            if text and link:
                inline_buttons.append({
                    'text': text,
                    'url': link
                })
                print(f"   ✅ Додано кнопку: {text} -> {link}")
            else:
                print(f"   ❌ Пропущено кнопку (порожня): text='{text}', link='{link}'")
        
        inline_buttons_json = json.dumps(inline_buttons) if inline_buttons else None
    
    if not name or not message_text:
        flash('Назва та текст розсилки не можуть бути порожніми!', 'error')
        return redirect(url_for('mailing_settings'))
    
    if media_type != "none" and not media_url:
        flash('URL або File ID медіа не може бути порожнім при виборі типу медіа!', 'error')
        return redirect(url_for('mailing_settings'))
    
    try:
        # Збираємо дані про фільтрацію користувачів
        user_filter = request.form.get('user_filter', 'all')
        user_status = request.form.get('user_status', '')
        
        print(f"🔍 DEBUG: Фільтр користувачів: {user_filter}")
        print(f"🔍 DEBUG: Статус користувачів: '{user_status}'")
        
        mailing_id = add_mailing(name, message_text, media_type, media_url, inline_buttons_json,
                                user_filter, user_status, None)
        
        # Перевіряємо, чи потрібно зробити розсилку повторюваною
        is_recurring = request.form.get('is_recurring') == 'on'
        
        if is_recurring:
            recurring_days = request.form.getlist('recurring_days')  # Використовуємо getlist для multiple select
            recurring_time = request.form.get('recurring_time')
            
            if recurring_days and recurring_time:
                # Конвертуємо дні в потрібний формат
                if isinstance(recurring_days, list):
                    days_str = ','.join(recurring_days)
                else:
                    days_str = recurring_days
                
                # Додаємо розсилку до повторюваних
                from database.settings_db import add_recurring_mailing
                recurring_success = add_recurring_mailing(mailing_id, days_str, recurring_time)
                
                if recurring_success:
                    flash(f'Розсилка "{name}" успішно створена та зроблена повторюваною!', 'success')
                else:
                    flash(f'Розсилка "{name}" створена, але не вдалося зробити її повторюваною!', 'warning')
            else:
                flash(f'Розсилка "{name}" створена, але для повторюваної розсилки потрібно вказати дні та час!', 'warning')
        else:
            flash(f'Розсилка "{name}" успішно створена!', 'success')
            
    except Exception as e:
        flash(f'Помилка при створенні розсилки: {str(e)}', 'error')
    
    return redirect(url_for('mailing_settings'))


@app.route('/create_and_send_mailing', methods=['POST'])
@login_required
def create_and_send_mailing_route():
    print("DEBUG: create_and_send_mailing_route called")
    print(f"DEBUG: form data: {request.form}")
    from database.settings_db import add_mailing, update_mailing_status
    from utils.cron_functions import send_mailing_to_users
    import asyncio
    import json
    
    try:
        name = request.form['mailing_name'].strip()
        message_text = request.form['message_text'].strip()
        media_type = request.form['media_type']
        media_url = request.form['media_url'].strip() if request.form['media_url'] else None
        
        # Парсимо inline кнопки
        # Спочатку перевіряємо, чи передано готовий JSON кнопок
        inline_buttons_json = request.form.get('inline_buttons')
        if inline_buttons_json and inline_buttons_json != 'null':
            try:
                # Перевіряємо, чи це валідний JSON
                json.loads(inline_buttons_json)
                print(f"✅ JSON кнопок валідний, використовуємо його")
            except json.JSONDecodeError:
                print(f"❌ JSON кнопок невалідний, парсимо поля окремо")
                inline_buttons_json = None
        
        # Якщо готовий JSON не передано, парсимо поля окремо
        if not inline_buttons_json or inline_buttons_json == 'null':
            button_texts = request.form.getlist('button_text[]')
            button_links = request.form.getlist('button_link[]')
            
            inline_buttons = []
            for i in range(len(button_texts)):
                text = button_texts[i].strip()
                link = button_links[i].strip()
                print(f"   Кнопка {i+1}: text='{text}', link='{link}'")
                
                if text and link:
                    inline_buttons.append({
                        'text': text,
                        'url': link
                    })
                    print(f"   ✅ Додано кнопку: {text} -> {link}")
                else:
                    print(f"   ❌ Пропущено кнопку (порожня): text='{text}', link='{link}'")
            
            inline_buttons_json = json.dumps(inline_buttons) if inline_buttons else None
        if not name or not message_text:
            return jsonify({'success': False, 'error': 'Назва та текст розсилки не можуть бути порожніми!'})
        
        if media_type != "none" and not media_url:
            return jsonify({'success': False, 'error': 'URL або File ID медіа не може бути порожнім при виборі типу медіа!'})
        
        # Збираємо дані про фільтрацію користувачів
        user_filter = request.form.get('user_filter', 'all')
        user_status = request.form.get('user_status', '')
        
        # Створюємо розсилку
        mailing_id = add_mailing(name, message_text, media_type, media_url, inline_buttons_json,
                                user_filter, user_status, None)
        
        # Перевіряємо, чи потрібно зробити розсилку повторюваною
        is_recurring = request.form.get('is_recurring') == 'on'
        
        if is_recurring:
            recurring_days = request.form.getlist('recurring_days')  # Використовуємо getlist для multiple select
            recurring_time = request.form.get('recurring_time')
            
            if recurring_days and recurring_time:
                # Конвертуємо дні в потрібний формат
                if isinstance(recurring_days, list):
                    days_str = ','.join(recurring_days)
                else:
                    days_str = recurring_days
                
                # Додаємо розсилку до повторюваних
                from database.settings_db import add_recurring_mailing
                recurring_success = add_recurring_mailing(mailing_id, days_str, recurring_time)
                
                if not recurring_success:
                    return jsonify({'success': False, 'error': 'Розсилка створена, але не вдалося зробити її повторюваною!'})
        
        # Запускаємо розсилку в БД
        update_mailing_status(mailing_id, 'active')

        bot = Bot(token=token)
        
        # Запускаємо розсилку асинхронно
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(send_mailing_to_users(bot, mailing_id))
            if result:
                if is_recurring:
                    return jsonify({'success': True, 'message': 'Розсилка успішно створена, запущена та зроблена повторюваною!'})
                else:
                    return jsonify({'success': True, 'message': 'Розсилка успішно створена та запущена!'})
            else:
                return jsonify({'success': False, 'error': 'Розсилка створена, але виникли помилки при відправці!'})
        finally:
            loop.close()
            # Правильно закриваємо сесію бота
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot.session.close())
                loop.close()
            except Exception as e:
                print(f"Помилка при закритті сесії бота: {e}")
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Помилка: {str(e)}'})


@app.route('/start_mailing/<int:mailing_id>')
@login_required
def start_mailing_route(mailing_id):
    from database.settings_db import update_mailing_status
    from utils.cron_functions import send_mailing_to_users
    import asyncio
    
    try:
        # Запускаємо розсилку в БД
        success = update_mailing_status(mailing_id, 'active')
        if not success:
            flash('Помилка при запуску розсилки!', 'error')
            return redirect(url_for('mailing_settings'))
        from aiogram import Bot
        bot = Bot(token=token)
        
        # Запускаємо розсилку асинхронно
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(send_mailing_to_users(bot, mailing_id))
            if result:
                flash('Розсилка успішно запущена та відправлена всім користувачам!', 'success')
            else:
                flash('Розсилка запущена, але виникли помилки при відправці!', 'error')
        finally:
            loop.close()
            # Правильно закриваємо сесію бота
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot.session.close())
                loop.close()
            except Exception as e:
                print(f"Помилка при закритті сесії бота: {e}")
        
    except Exception as e:
        flash(f'Помилка при запуску розсилки: {str(e)}', 'error')
    
    return redirect(url_for('mailing_settings'))


@app.route('/delete_mailing/<int:mailing_id>')
@login_required
def delete_mailing_route(mailing_id):
    print(f"DEBUG: delete_mailing_route called with mailing_id: {mailing_id}")
    from database.settings_db import delete_mailing
    
    try:
        success = delete_mailing(mailing_id)
        if success:
            print(f"DEBUG: mailing deleted successfully for ID: {mailing_id}")
            flash('Розсилка успішно видалена!', 'success')
        else:
            print(f"DEBUG: failed to delete mailing for ID: {mailing_id}")
            flash('Помилка при видаленні!', 'error')
    except Exception as e:
        print(f"ERROR in delete_mailing_route: {e}")
        flash(f'Помилка при видаленні: {str(e)}', 'error')
    
    return redirect(url_for('mailing_settings'))


@app.route('/cancel_scheduled_mailing/<int:mailing_id>')
@login_required
def cancel_scheduled_mailing_route(mailing_id):
    print(f"DEBUG: cancel_scheduled_mailing_route called with mailing_id: {mailing_id}")
    from database.settings_db import cancel_scheduled_mailing
    
    try:
        success = cancel_scheduled_mailing(mailing_id)
        if success:
            print(f"DEBUG: scheduled mailing cancelled successfully for ID: {mailing_id}")
            flash('Планування розсилки успішно скасовано!', 'success')
        else:
            print(f"DEBUG: failed to cancel scheduled mailing for ID: {mailing_id}")
            flash('Помилка при скасуванні планування!', 'error')
    except Exception as e:
        print(f"ERROR in cancel_scheduled_mailing_route: {e}")
        flash(f'Помилка при скасуванні планування: {str(e)}', 'error')
    
    return redirect(url_for('mailing_settings'))


@app.route('/toggle_recurring_mailing/<int:mailing_id>', methods=['POST'])
@login_required
def toggle_recurring_mailing_route(mailing_id):
    """Включає/виключає повторювану розсилку"""
    print(f"DEBUG: toggle_recurring_mailing_route called with mailing_id: {mailing_id}")
    print(f"DEBUG: form data: {request.form}")
    from database.settings_db import toggle_recurring_mailing
    
    try:
        is_recurring = request.form.get('is_recurring') == 'true'
        recurring_days = request.form.get('recurring_days', '')
        recurring_time = request.form.get('recurring_time', '')
        
        success = toggle_recurring_mailing(mailing_id, is_recurring, recurring_days, recurring_time)
        if success:
            if is_recurring:
                print(f"DEBUG: mailing set as recurring for ID: {mailing_id}")
                flash('Розсилка успішно налаштована як повторювана!', 'success')
            else:
                print(f"DEBUG: mailing recurring disabled for ID: {mailing_id}")
                flash('Повторювана розсилка успішно вимкнена!', 'success')
        else:
            print(f"DEBUG: failed to toggle recurring mailing for ID: {mailing_id}")
            flash('Помилка при налаштуванні повторюваної розсилки!', 'error')
    except Exception as e:
        print(f"ERROR in toggle_recurring_mailing_route: {e}")
        flash(f'Помилка при налаштуванні: {str(e)}', 'error')
    
    return redirect(url_for('mailing_settings'))


@app.route('/resend_mailing/<int:mailing_id>')
@login_required
def resend_mailing_route(mailing_id):
    """Відправляє розсилку знову"""
    print(f"DEBUG: resend_mailing_route called with mailing_id: {mailing_id}")
    from database.settings_db import resend_mailing
    from utils.cron_functions import send_mailing_to_users
    import asyncio
    
    try:
        # Оновлюємо час відправки в БД
        success = resend_mailing(mailing_id)
        if not success:
            print(f"DEBUG: failed to update mailing time for ID: {mailing_id}")
            flash('Помилка при оновленні часу відправки!', 'error')
            return redirect(url_for('mailing_settings'))
        
        # Відправляємо розсилку знову
        from aiogram import Bot
        bot = Bot(token=token)
        
        # Запускаємо розсилку асинхронно
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(send_mailing_to_users(bot, mailing_id))
            if result:
                print(f"DEBUG: mailing resent successfully for ID: {mailing_id}")
                flash('Розсилка успішно відправлена знову!', 'success')
            else:
                print(f"DEBUG: mailing updated but failed to send for ID: {mailing_id}")
                flash('Розсилка оновлена, але виникли помилки при відправці!', 'error')
        finally:
            loop.close()
            # Правильно закриваємо сесію бота
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot.session.close())
                loop.close()
            except Exception as e:
                print(f"Помилка при закритті сесії бота: {e}")
        
    except Exception as e:
        flash(f'Помилка при повторній відправці: {str(e)}', 'error')
    
    return redirect(url_for('mailing_settings'))


@app.route('/create_and_schedule_mailing', methods=['POST'])
@login_required
def create_and_schedule_mailing_route():
    from database.settings_db import add_mailing, schedule_mailing
    import json
    
    try:
        name = request.form['mailing_name'].strip()
        message_text = request.form['message_text'].strip()
        media_type = request.form['media_type']
        media_url = request.form['media_url'].strip() if request.form['media_url'] else None
        
        for key in request.form.keys():
            print(f"   {key}: {request.form[key]}")
        
        # Спочатку перевіряємо, чи передано готовий JSON кнопок
        inline_buttons_json = request.form.get('inline_buttons')
        if inline_buttons_json and inline_buttons_json != 'null':
            try:
                # Перевіряємо, чи це валідний JSON
                json.loads(inline_buttons_json)
                print(f"✅ JSON кнопок валідний, використовуємо його")
            except json.JSONDecodeError:
                print(f"❌ JSON кнопок невалідний, парсимо поля окремо")
                inline_buttons_json = None
        
        # Якщо готовий JSON не передано, парсимо поля окремо
        if not inline_buttons_json or inline_buttons_json == 'null':
            button_texts = request.form.getlist('button_text[]')
            button_links = request.form.getlist('button_link[]')
            
            inline_buttons = []
            for i in range(len(button_texts)):
                text = button_texts[i].strip()
                link = button_links[i].strip()
                
                if text and link:
                    inline_buttons.append({
                        'text': text,
                        'url': link
                    })
            
            inline_buttons_json = json.dumps(inline_buttons) if inline_buttons else None
        
        if not name or not message_text:
            return jsonify({'success': False, 'error': 'Назва та текст розсилки не можуть бути порожніми!'})
        
        if media_type != "none" and not media_url:
            return jsonify({'success': False, 'error': 'URL або File ID медіа не може бути порожнім при виборі типу медіа!'})
        
        # Збираємо дані про фільтрацію користувачів
        user_filter = request.form.get('user_filter', 'all')
        user_status = request.form.get('user_status', '')
        
        # Створюємо розсилку
        mailing_id = add_mailing(name, message_text, media_type, media_url, inline_buttons_json,
                                user_filter, user_status, None)
        
        # Плануємо розсилку
        schedule_type = request.form.get('schedule_type', 'immediate')
        
        if schedule_type == 'scheduled':
            schedule_datetime = request.form.get('schedule_datetime')
            
            if schedule_datetime:
                # Конвертуємо київський час в UTC для збереження
                from database.settings_db import kyiv_to_utc_time
                
                utc_time_str = kyiv_to_utc_time(schedule_datetime)
                
                # Плануємо розсилку
                schedule_mailing(mailing_id, utc_time_str)
                
                # Перевіряємо, чи потрібно зробити розсилку повторюваною
                is_recurring = request.form.get('is_recurring') == 'on'
                
                if is_recurring:
                    recurring_days = request.form.getlist('recurring_days')  # Використовуємо getlist для multiple select
                    recurring_time = request.form.get('recurring_time')
                    
                    if recurring_days and recurring_time:
                        # Конвертуємо дні в потрібний формат
                        if isinstance(recurring_days, list):
                            days_str = ','.join(recurring_days)
                        else:
                            days_str = recurring_days
                        
                        # Додаємо розсилку до повторюваних
                        from database.settings_db import add_recurring_mailing
                        recurring_success = add_recurring_mailing(mailing_id, days_str, recurring_time)
                        
                        if recurring_success:
                            from database.settings_db import utc_to_kyiv_time
                            kyiv_display_time = utc_to_kyiv_time(utc_time_str)
                            return jsonify({
                                'success': True, 
                                'message': f'Розсилка "{name}" створена, запланована на {kyiv_display_time} (Київ) та зроблена повторюваною!'
                            })
                        else:
                            return jsonify({
                                'success': False, 
                                'error': 'Розсилка створена та запланована, але не вдалося зробити її повторюваною!'
                            })
                    else:
                        return jsonify({
                            'success': False, 
                            'error': 'Для повторюваної розсилки потрібно вказати дні та час!'
                        })
                else:
                    from database.settings_db import utc_to_kyiv_time
                    kyiv_display_time = utc_to_kyiv_time(utc_time_str)
                    return jsonify({
                        'success': True, 
                        'message': f'Розсилка "{name}" створена та запланована на {kyiv_display_time} (Київ)!'
                    })
            else:
                return jsonify({'success': False, 'error': 'Не вказано час для планування!'})
        else:
            return jsonify({'success': True, 'message': f'Розсилка "{name}" створена!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Помилка: {str(e)}'})


@app.route('/subscription-messages')
@login_required
def subscription_messages():
    """Сторінка налаштування повідомлень після перевірки підписки"""
    print("DEBUG: subscription_messages route called")
    current_message = get_subscription_message()
    print(f"DEBUG: current_message: {current_message}")
    return render_template('subscription_messages.html', current_message=current_message)





@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    print(f"DEBUG: change_password route called with method: {request.method}")
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Перевіряємо, чи новий пароль не порожній
        if not new_password or len(new_password.strip()) < 6:
            flash('Новый пароль должен быть не менее 6 символов!', 'error')
            return render_template('change_password.html')
        
        # Перевіряємо, чи паролі співпадають
        if new_password != confirm_password:
            flash('Новые пароли не совпадают!', 'error')
            return render_template('change_password.html')
        
        # Змінюємо пароль
        new_password_hash = generate_password_hash(new_password.strip())
        update_admin_password(new_password_hash)
        
        print("DEBUG: password changed successfully")
        flash('Пароль успешно изменен!', 'success')
        return redirect(url_for('admin_panel'))
    
    return render_template('change_password.html')


@app.route('/edit_mailing/<int:mailing_id>')
@login_required
def edit_mailing(mailing_id):
    """Сторінка редагування розсилки"""
    print(f"DEBUG: edit_mailing route called with mailing_id: {mailing_id}")
    from database.settings_db import get_mailing_by_id
    from datetime import datetime
    import pytz
    
    mailing = get_mailing_by_id(mailing_id)
    if not mailing:
        print(f"DEBUG: mailing not found for ID: {mailing_id}")
        flash('Розсилку не знайдено!', 'error')
        return redirect(url_for('mailing_settings'))
    
    # Конвертуємо UTC час в київський для відображення
    if mailing.get('scheduled_at'):
        from database.settings_db import utc_to_kyiv_time
        mailing['scheduled_at_kyiv'] = utc_to_kyiv_time(mailing['scheduled_at'])
        print(f"DEBUG: UTC time: {mailing['scheduled_at']}")
        print(f"DEBUG: Kyiv time formatted: {mailing['scheduled_at_kyiv']}")
    else:
        mailing['scheduled_at_kyiv'] = None
    
    print(f"DEBUG: mailing found: {mailing}")
    print(f"DEBUG: mailing type: {type(mailing)}")
    if mailing:
        print(f"DEBUG: mailing keys: {mailing.keys() if isinstance(mailing, dict) else 'Not a dict'}")
    return render_template('edit_mailing.html', mailing=mailing)

@app.route('/update_mailing/<int:mailing_id>', methods=['POST'])
@login_required
def update_mailing(mailing_id):
    """Оновлення розсилки"""
    import traceback
    print(f"DEBUG: update_mailing route called with mailing_id: {mailing_id}")
    print(f"DEBUG: form data: {request.form}")
    from database.settings_db import update_mailing_data, update_mailing_scheduled_time
    
    try:
        # Отримуємо дані з форми
        mailing_name = request.form.get('mailing_name', '').strip()
        message_text = request.form.get('message_text', '').strip()
        media_type = request.form.get('media_type', 'none')
        media_url = request.form.get('media_url', '').strip()
        scheduled_time = request.form.get('scheduled_time', '').strip()
        
        print(f"DEBUG: scheduled_time from form: '{scheduled_time}'")
        print(f"DEBUG: scheduled_time type: {type(scheduled_time)}")
        print(f"DEBUG: scheduled_time is empty: {scheduled_time == ''}")
        print(f"DEBUG: scheduled_time is None: {scheduled_time is None}")
        
        if not mailing_name or not message_text:
            flash('Назва та текст розсилки не можуть бути порожніми!', 'error')
            return redirect(url_for('edit_mailing', mailing_id=mailing_id))
        
        if media_type != "none" and not media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('edit_mailing', mailing_id=mailing_id))
        
        # Обробка інлайн кнопок
        button_texts = request.form.getlist('button_text[]')
        button_links = request.form.getlist('button_link[]')
        
        inline_buttons = []
        for i in range(len(button_texts)):
            if button_texts[i].strip() and button_links[i].strip():
                text = button_texts[i].strip()[:64]
                url = button_links[i].strip()[:2048]
                
                inline_buttons.append({
                    'text': text,
                    'url': url
                })
        
        if len(inline_buttons) > 8:
            inline_buttons = inline_buttons[:8]
            flash('Додано тільки перші 8 кнопок (обмеження Telegram)', 'error')
        
        # Оновлюємо дані розсилки
        success = update_mailing_data(
            mailing_id=mailing_id,
            name=mailing_name,
            message_text=message_text,
            media_type=media_type,
            media_url=media_url,
            inline_buttons=json.dumps(inline_buttons)
        )
        
        # Якщо є новий час розсилки, оновлюємо його
        print(f"DEBUG: About to check scheduled_time: '{scheduled_time}'")
        if scheduled_time:
            print(f"DEBUG: scheduled_time is not empty, processing...")
            try:
                # Конвертуємо київський час в UTC для збереження
                from database.settings_db import kyiv_to_utc_time
                
                print(f"DEBUG: Parsing datetime from: '{scheduled_time}'")
                utc_time_str = kyiv_to_utc_time(scheduled_time)
                print(f"DEBUG: UTC time ISO format: {utc_time_str}")
                
                time_success = update_mailing_scheduled_time(mailing_id, utc_time_str)
                if time_success:
                    print(f"DEBUG: scheduled time updated successfully for mailing ID: {mailing_id}")
                else:
                    print(f"DEBUG: failed to update scheduled time for mailing ID: {mailing_id}")
                    
            except Exception as e:
                print(f"ERROR updating scheduled time: {e}")
                print(f"ERROR traceback: {traceback.format_exc()}")
                flash('Помилка при оновленні часу розсилки!', 'error')
        else:
            print(f"DEBUG: scheduled_time is empty, skipping time update")
        
        # Обработка повторяющихся рассылок
        is_recurring = request.form.get('is_recurring') == '1'
        recurring_time = request.form.get('recurring_time')
        recurring_days = request.form.getlist('recurring_days[]')
        
        print(f"DEBUG: is_recurring: {is_recurring}, recurring_time: {recurring_time}, recurring_days: {recurring_days}")
        
        if is_recurring and recurring_time and recurring_days:
            print(f"DEBUG: Processing recurring mailing update - time: {recurring_time}, days: {recurring_days}")
            try:
                from database.settings_db import update_recurring_mailing, add_recurring_mailing
                
                # Конвертируем дни в строку
                days_str = ','.join(recurring_days)
                
                # Проверяем, существует ли уже повторяющаяся рассылка
                from database.settings_db import get_mailing_by_id
                mailing_data = get_mailing_by_id(mailing_id)
                
                if mailing_data and mailing_data.get('is_recurring'):
                    # Обновляем существующую повторяющуюся рассылку
                    recurring_success = update_recurring_mailing(mailing_id, days_str, recurring_time)
                else:
                    # Создаем новую повторяющуюся рассылку
                    recurring_success = add_recurring_mailing(mailing_id, days_str, recurring_time)
                
                if recurring_success:
                    print(f"DEBUG: recurring mailing updated successfully for ID: {mailing_id}")
                else:
                    print(f"DEBUG: failed to update recurring mailing for ID: {mailing_id}")
                    flash('Помилка при оновленні повторюваної розсилки!', 'error')
                    
            except Exception as e:
                print(f"ERROR updating recurring mailing: {e}")
                print(f"ERROR traceback: {traceback.format_exc()}")
                flash('Помилка при оновленні повторюваної розсилки!', 'error')
        elif not is_recurring:
            # Если галочка снята, удаляем повторяющуюся рассылку
            try:
                from database.settings_db import remove_recurring_mailing
                remove_recurring_mailing(mailing_id)
                print(f"DEBUG: recurring mailing removed for ID: {mailing_id}")
            except Exception as e:
                print(f"ERROR removing recurring mailing: {e}")
                flash('Помилка при видаленні повторюваної розсилки!', 'error')
        
        if success:
            print(f"DEBUG: mailing updated successfully for ID: {mailing_id}")
            flash('Розсилку успішно оновлено!', 'success')
        else:
            print(f"DEBUG: failed to update mailing for ID: {mailing_id}")
            flash('Помилка при оновленні розсилки!', 'error')
        
        return redirect(url_for('mailing_settings'))
        
    except Exception as e:
        print(f"ERROR in update_mailing: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('edit_mailing', mailing_id=mailing_id))





@app.route('/save_subscription_message', methods=['POST'])
@login_required
def save_subscription_message_route():
    """Збереження повідомлення після перевірки підписки з інлайн кнопками"""
    try:
        message_text = request.form.get('message_text', '').strip()
        media_type = request.form.get('media_type', 'none')
        media_url = request.form.get('media_url', '').strip()
        inline_buttons_position = request.form.get('inline_buttons_position', 'below')
        
        if not message_text:
            flash('Текст повідомлення не може бути порожнім!', 'error')
            return redirect(url_for('subscription_messages'))
        
        if media_type != "none" and not media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('subscription_messages'))
        
        # Обробка інлайн кнопок
        button_texts = request.form.getlist('button_text[]')
        button_links = request.form.getlist('button_link[]')
        
        inline_buttons = []
        for i in range(len(button_texts)):
            if button_texts[i].strip() and button_links[i].strip():
                text = button_texts[i].strip()[:64]
                url = button_links[i].strip()[:2048]
                
                inline_buttons.append({
                    'text': text,
                    'url': url
                })
        
        if len(inline_buttons) > 8:
            inline_buttons = inline_buttons[:8]
            flash('Додано тільки перші 8 кнопок (обмеження Telegram)', 'error')
        
        # Зберігаємо повідомлення з інлайн кнопками
        success = save_subscription_message_with_buttons(
            message_text=message_text,
            media_type=media_type,
            media_url=media_url,
            inline_buttons=inline_buttons,
            inline_buttons_position=inline_buttons_position
        )
        
        if success:
            flash('Повідомлення після перевірки підписки успішно збережено!', 'success')
        else:
            flash('Помилка при збереженні повідомлення!', 'error')
        
        return redirect(url_for('subscription_messages'))
        
    except Exception as e:
        print(f"ERROR in save_subscription_message_route: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('subscription_messages'))


@app.route('/save_captcha_settings', methods=['POST'])
@login_required
def save_captcha_settings_route():
    """Збереження глобальних налаштувань капчі"""
    try:
        captcha_message = request.form.get('captcha_message', '').strip()
        captcha_media_type = request.form.get('captcha_media_type', 'none')
        captcha_media_url = request.form.get('captcha_media_url', '').strip()
        captcha_button_text = request.form.get('captcha_button_text', 'Я не робот').strip()
        
        if not captcha_message:
            flash('Текст капчі не може бути порожнім!', 'error')
            return redirect(url_for('captcha_settings'))
        
        if captcha_media_type != "none" and not captcha_media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('captcha_settings'))
        
        # Зберігаємо глобальні налаштування капчі
        success = save_captcha_settings(
            captcha_message=captcha_message,
            captcha_media_type=captcha_media_type,
            captcha_media_url=captcha_media_url,
            captcha_button_text=captcha_button_text
        )
        
        if success:
            flash('Налаштування капчі успішно збережено!', 'success')
        else:
            flash('Помилка при збереженні налаштувань капчі!', 'error')
        
        return redirect(url_for('captcha_settings'))
        
    except Exception as e:
        print(f"ERROR in save_captcha_settings_route: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('captcha_settings'))


@app.route('/save_answers_settings', methods=['POST'])
@login_required
def save_answers_settings_route():
    """Збереження налаштувань повідомлення 'Ответы на вопросы'"""
    try:
        message = request.form.get('message', '').strip()
        media_type = request.form.get('media_type', 'none')
        media_url = request.form.get('media_url', '').strip()
        
        if not message:
            flash('Текст повідомлення не може бути порожнім!', 'error')
            return redirect(url_for('answers_settings'))
        
        if media_type != "none" and not media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('answers_settings'))
        
        # Обробка інлайн кнопок
        button_texts = request.form.getlist('button_text[]')
        button_links = request.form.getlist('button_link[]')
        
        inline_buttons = []
        for i in range(len(button_texts)):
            if button_texts[i].strip() and button_links[i].strip():
                text = button_texts[i].strip()[:64]
                url = button_links[i].strip()[:2048]
                
                inline_buttons.append({
                    'text': text,
                    'url': url
                })
        
        if len(inline_buttons) > 8:
            inline_buttons = inline_buttons[:8]
            flash('Додано тільки перші 8 кнопок (обмеження Telegram)', 'error')
        
        # Зберігаємо налаштування
        success = save_answers_config(
            message=message,
            media_type=media_type,
            media_url=media_url,
            inline_buttons=inline_buttons
        )
        
        if success:
            flash('Налаштування повідомлення "Ответы на вопросы" успішно збережено!', 'success')
        else:
            flash('Помилка при збереженні налаштувань!', 'error')
        
        return redirect(url_for('answers_settings'))
        
    except Exception as e:
        print(f"ERROR in save_answers_settings_route: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('answers_settings'))


@app.route('/save_private_lesson_settings', methods=['POST'])
@login_required
def save_private_lesson_settings_route():
    """Збереження налаштувань повідомлення 'Приватный урок'"""
    try:
        message = request.form.get('message', '').strip()
        media_type = request.form.get('media_type', 'none')
        media_url = request.form.get('media_url', '').strip()
        
        if not message:
            flash('Текст повідомлення не може бути порожнім!', 'error')
            return redirect(url_for('private_lesson_settings'))
        
        if media_type != "none" and not media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('private_lesson_settings'))
        
        # Обробка інлайн кнопок
        button_texts = request.form.getlist('button_text[]')
        button_links = request.form.getlist('button_link[]')
        
        inline_buttons = []
        for i in range(len(button_texts)):
            if button_texts[i].strip() and button_links[i].strip():
                text = button_texts[i].strip()[:64]
                url = button_links[i].strip()[:2048]
                
                inline_buttons.append({
                    'text': text,
                    'url': url
                })
        
        if len(inline_buttons) > 8:
            inline_buttons = inline_buttons[:8]
            flash('Додано тільки перші 8 кнопок (обмеження Telegram)', 'error')
        
        # Зберігаємо налаштування
        success = save_private_lesson_config(
            message=message,
            media_type=media_type,
            media_url=media_url,
            inline_buttons=inline_buttons
        )
        
        if success:
            flash('Налаштування повідомлення "Приватный урок" успішно збережено!', 'success')
        else:
            flash('Помилка при збереженні налаштувань!', 'error')
        
        return redirect(url_for('private_lesson_settings'))
        
    except Exception as e:
        print(f"ERROR in save_private_lesson_settings_route: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('private_lesson_settings'))


@app.route('/save_tariffs_settings', methods=['POST'])
@login_required
def save_tariffs_settings_route():
    """Збереження налаштувань повідомлення 'Посмотреть тарифы'"""
    try:
        message = request.form.get('message', '').strip()
        media_type = request.form.get('media_type', 'none')
        media_url = request.form.get('media_url', '').strip()
        
        if not message:
            flash('Текст повідомлення не може бути порожнім!', 'error')
            return redirect(url_for('tariffs_settings'))
        
        if media_type != "none" and not media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('tariffs_settings'))
        
        # Обробка інлайн кнопок
        button_texts = request.form.getlist('button_text[]')
        button_links = request.form.getlist('button_link[]')
        
        inline_buttons = []
        for i in range(len(button_texts)):
            if button_texts[i].strip() and button_links[i].strip():
                text = button_texts[i].strip()[:64]
                url = button_links[i].strip()[:2048]
                
                inline_buttons.append({
                    'text': text,
                    'url': url
                })
        
        if len(inline_buttons) > 8:
            inline_buttons = inline_buttons[:8]
            flash('Додано тільки перші 8 кнопок (обмеження Telegram)', 'error')
        
        # Отримуємо тексти кнопок
        clothes_button_text = request.form.get('clothes_button_text', '').strip()
        tech_button_text = request.form.get('tech_button_text', '').strip()
        
        print(f"DEBUG: clothes_button_text = '{clothes_button_text}'")
        print(f"DEBUG: tech_button_text = '{tech_button_text}'")
        
        if not clothes_button_text or not tech_button_text:
            flash('Тексти кнопок не можуть бути порожніми!', 'error')
            return redirect(url_for('tariffs_settings'))
        
        # Зберігаємо налаштування
        success = save_tariffs_config(
            message=message,
            media_type=media_type,
            media_url=media_url,
            inline_buttons=inline_buttons
        )
        
        # Зберігаємо налаштування кнопок вибору тарифів окремо
        if success:
            from database.settings_db import save_tariff_selection_buttons_config
            
            print(f"DEBUG: Зберігаємо clothes_button_text = '{clothes_button_text}'")
            print(f"DEBUG: Зберігаємо tech_button_text = '{tech_button_text}'")
            
            buttons_success = save_tariff_selection_buttons_config(
                clothes_button_text=clothes_button_text,
                tech_button_text=tech_button_text
            )
            
            print(f"DEBUG: buttons_success = {buttons_success}")
            
            if buttons_success:
                flash('Налаштування повідомлення "Посмотреть тарифы" успішно збережено!', 'success')
            else:
                flash('Частично збережено налаштування!', 'warning')
        else:
            flash('Помилка при збереженні налаштувань!', 'error')
        
        return redirect(url_for('tariffs_settings'))
        
    except Exception as e:
        print(f"ERROR in save_tariffs_settings_route: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('tariffs_settings'))


# Маршрути для налаштувань тарифів
@app.route('/clothes-tariff-settings')
@login_required
def clothes_tariff_settings():
    """Сторінка налаштувань тарифу 'Одежда'"""
    clothes_config = get_clothes_tariff_config()
    return render_template('clothes_tariff_settings.html', clothes_config=clothes_config)


@app.route('/clothes-tariff-settings', methods=['POST'])
@login_required
def save_clothes_tariff_settings():
    """Збереження налаштувань тарифу 'Одежда'"""
    try:
        message = request.form.get('message', '').strip()
        media_type = request.form.get('media_type', 'none')
        media_url = request.form.get('media_url', '').strip()
        
        if not message:
            flash('Текст повідомлення не може бути порожнім!', 'error')
            return redirect(url_for('clothes_tariff_settings'))
        
        if media_type != "none" and not media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('clothes_tariff_settings'))
        
        button_text = request.form.get('button_text', '').strip()
        
        if not button_text:
            flash('Текст кнопки не може бути порожнім!', 'error')
            return redirect(url_for('clothes_tariff_settings'))
        
        # Зберігаємо налаштування
        success = save_clothes_tariff_config(
            message=message,
            media_type=media_type,
            media_url=media_url,
            button_text=button_text
        )
        
        if success:
            flash('Налаштування тарифу "Одежда" успішно збережено!', 'success')
        else:
            flash('Помилка при збереженні налаштувань!', 'error')
        
        return redirect(url_for('clothes_tariff_settings'))
        
    except Exception as e:
        print(f"ERROR in save_clothes_tariff_settings: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('clothes_tariff_settings'))


@app.route('/tech-tariff-settings')
@login_required
def tech_tariff_settings():
    """Сторінка налаштувань тарифу 'Техника'"""
    tech_config = get_tech_tariff_config()
    return render_template('tech_tariff_settings.html', tech_config=tech_config)


@app.route('/tech-tariff-settings', methods=['POST'])
@login_required
def save_tech_tariff_settings():
    """Збереження налаштувань тарифу 'Техника'"""
    try:
        message = request.form.get('message', '').strip()
        media_type = request.form.get('media_type', 'none')
        media_url = request.form.get('media_url', '').strip()
        
        if not message:
            flash('Текст повідомлення не може бути порожнім!', 'error')
            return redirect(url_for('tech_tariff_settings'))
        
        if media_type != "none" and not media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('tech_tariff_settings'))
        
        button_text = request.form.get('button_text', '').strip()
        
        if not button_text:
            flash('Текст кнопки не може бути порожнім!', 'error')
            return redirect(url_for('tech_tariff_settings'))
        
        # Зберігаємо налаштування
        success = save_tech_tariff_config(
            message=message,
            media_type=media_type,
            media_url=media_url,
            button_text=button_text
        )
        
        if success:
            flash('Налаштування тарифу "Техника" успішно збережено!', 'success')
        else:
            flash('Помилка при збереженні налаштувань!', 'error')
        
        return redirect(url_for('tech_tariff_settings'))
        
    except Exception as e:
        print(f"ERROR in save_tech_tariff_settings: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('tech_tariff_settings'))


@app.route('/clothes-payment-settings')
@login_required
def clothes_payment_settings():
    """Сторінка налаштувань оплати тарифу 'Одежда'"""
    clothes_payment_config = get_clothes_payment_config()
    return render_template('clothes_payment_settings.html', clothes_payment_config=clothes_payment_config)


@app.route('/clothes-payment-settings', methods=['POST'])
@login_required
def save_clothes_payment_settings():
    """Збереження налаштувань оплати тарифу 'Одежда'"""
    try:
        message = request.form.get('message', '').strip()
        media_type = request.form.get('media_type', 'none')
        media_url = request.form.get('media_url', '').strip()
        
        if not message:
            flash('Текст повідомлення не може бути порожнім!', 'error')
            return redirect(url_for('clothes_payment_settings'))
        
        if media_type != "none" and not media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('clothes_payment_settings'))
        
        back_button_text = request.form.get('back_button_text', '').strip()
        main_menu_button_text = request.form.get('main_menu_button_text', '').strip()
        
        if not back_button_text or not main_menu_button_text:
            flash('Тексти кнопок не можуть бути порожніми!', 'error')
            return redirect(url_for('clothes_payment_settings'))
        
        # Отримуємо налаштування для включення/виключення кнопок
        show_back_button = request.form.get('show_back_button_value') == '1'
        show_main_menu_button = request.form.get('show_main_menu_button_value') == '1'
        
        # Зберігаємо налаштування
        success = save_clothes_payment_config(
            message=message,
            media_type=media_type,
            media_url=media_url,
            back_button_text=back_button_text,
            main_menu_button_text=main_menu_button_text,
            show_back_button=show_back_button,
            show_main_menu_button=show_main_menu_button
        )
        
        if success:
            flash('Налаштування оплати тарифу "Одежда" успішно збережено!', 'success')
        else:
            flash('Помилка при збереженні налаштувань!', 'error')
        
        return redirect(url_for('clothes_payment_settings'))
        
    except Exception as e:
        print(f"ERROR in save_clothes_payment_settings: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('clothes_payment_settings'))


@app.route('/tech-payment-settings')
@login_required
def tech_payment_settings():
    """Сторінка налаштувань оплати тарифу 'Техника'"""
    tech_payment_config = get_tech_payment_config()
    return render_template('tech_payment_settings.html', tech_payment_config=tech_payment_config)


@app.route('/tech-payment-settings', methods=['POST'])
@login_required
def save_tech_payment_settings():
    try:
        message = request.form.get('message', '').strip()
        media_type = request.form.get('media_type', 'none')
        media_url = request.form.get('media_url', '').strip()
        
        if not message:
            flash('Текст повідомлення не може бути порожнім!', 'error')
            return redirect(url_for('tech_payment_settings'))
        
        if media_type != "none" and not media_url:
            flash('URL медіа не може бути порожнім при виборі типу медіа!', 'error')
            return redirect(url_for('tech_payment_settings'))
        
        back_button_text = request.form.get('back_button_text', '').strip()
        main_menu_button_text = request.form.get('main_menu_button_text', '').strip()
        
        if not back_button_text or not main_menu_button_text:
            flash('Тексти кнопок не можуть бути порожніми!', 'error')
            return redirect(url_for('tech_payment_settings'))
        
        # Отримуємо налаштування для включення/виключення кнопок
        show_back_button = request.form.get('show_back_button_value') == '1'
        show_main_menu_button = request.form.get('show_main_menu_button_value') == '1'
        
        # Зберігаємо налаштування
        success = save_tech_payment_config(
            message=message,
            media_type=media_type,
            media_url=media_url,
            back_button_text=back_button_text,
            main_menu_button_text=main_menu_button_text,
            show_back_button=show_back_button,
            show_main_menu_button=show_main_menu_button
        )
        
        if success:
            flash('Налаштування оплати тарифу "Техника" успішно збережено!', 'success')
        else:
            flash('Помилка при збереженні налаштувань!', 'error')
        
        return redirect(url_for('tech_payment_settings'))
        
    except Exception as e:
        print(f"ERROR in save_tech_payment_settings: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('tech_payment_settings'))


# Обробка помилки 404
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.route('/update-user-status', methods=['POST'])
@login_required
def update_user_status_route():
    """Оновлення статусу користувача адміном"""
    try:
        user_id = request.form.get('user_id', type=int)
        new_status = request.form.get('new_status', '').strip()
        
        if not user_id or not new_status:
            flash('Помилка: відсутні необхідні дані', 'error')
            return redirect(url_for('users_list'))
        
        success = admin_update_user_status(user_id, new_status)
        
        if success:
            flash(f'✅ Статус користувача {user_id} успішно оновлено на "{new_status}"', 'success')
        else:
            flash(f'❌ Помилка при оновленні статусу користувача {user_id}', 'error')
        
        return redirect(url_for('users_list'))
        
    except Exception as e:
        print(f"ERROR in update_user_status_route: {e}")
        flash(f'Помилка: {str(e)}', 'error')
        return redirect(url_for('users_list'))


@app.route('/api/update-user-status', methods=['POST'])
@login_required
def api_update_user_status():
    """AJAX endpoint для оновлення статусу користувача"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_status = data.get('new_status', '').strip()
        
        if not user_id or not new_status:
            return jsonify({'success': False, 'error': 'Відсутні необхідні дані'})
        
        success = admin_update_user_status(user_id, new_status)
        
        if success:
            return jsonify({'success': True, 'message': f'Статус користувача {user_id} успішно оновлено на "{new_status}"'})
        else:
            return jsonify({'success': False, 'error': f'Помилка при оновленні статусу користувача {user_id}'})
        
    except Exception as e:
        print(f"ERROR in api_update_user_status: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/delete-user', methods=['POST'])
@login_required
def api_delete_user():
    """AJAX endpoint для удаления пользователя"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Отсутствует ID пользователя'})
        
        success = admin_delete_user(user_id)
        
        if success:
            return jsonify({'success': True, 'message': f'Пользователь {user_id} успешно удален'})
        else:
            return jsonify({'success': False, 'error': f'Ошибка при удалении пользователя {user_id}'})
        
    except Exception as e:
        print(f"ERROR in api_delete_user: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/get-stats', methods=['GET'])
@login_required
def api_get_stats():
    """AJAX endpoint для получения статистики"""
    try:
        total_users = get_users_count()
        subscription_stats = get_subscription_stats()
        
        return jsonify({
            'success': True,
            'total_users': total_users,
            'subscription_stats': subscription_stats
        })
        
    except Exception as e:
        print(f"ERROR in api_get_stats: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/analytics/summary')
@login_required
def api_analytics_summary():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        param = request.args.get('param')
        data = get_analytics_counts(start_date, end_date, param)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        print(f"ERROR in api_analytics_summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analytics/timeseries')
@login_required
def api_analytics_timeseries():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        param = request.args.get('param')
        series = get_analytics_timeseries(start_date, end_date, param)
        # Convert tuples to dicts for JSON
        items = [{
            'day': d,
            'joined': j,
            'to_payment': p,
            'paid': paid
        } for (d, j, p, paid) in series]
        return jsonify({'success': True, 'data': items})
    except Exception as e:
        print(f"ERROR in api_analytics_timeseries: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analytics/params')
@login_required
def api_analytics_params():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        dist = get_param_distribution(start_date, end_date)
        items = [{'param_name': name, 'count': cnt} for (name, cnt) in dist]
        return jsonify({'success': True, 'data': items})
    except Exception as e:
        print(f"ERROR in api_analytics_params: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analytics/statuses')
@login_required
def api_analytics_statuses():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        param = request.args.get('param')
        dist = get_status_distribution(start_date, end_date, param)
        items = [{'status': name, 'count': cnt} for (name, cnt) in dist]
        return jsonify({'success': True, 'data': items})
    except Exception as e:
        print(f"ERROR in api_analytics_statuses: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    
    app.run(debug=True, host='0.0.0.0', port=5001)
