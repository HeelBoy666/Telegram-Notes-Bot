// Основной JavaScript файл для админ-панели

// Глобальные переменные
let refreshInterval;
let currentPage = 1;
let realtimeStatsInterval;

// Управление темой
let currentTheme = localStorage.getItem('theme') || 'light';

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация темы
    initTheme();
    updateThemeIcon();
    
    // Инициализация тултипов
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Инициализация popover'ов для пользователей
    initUserPopovers();
    
    // Инициализация других функций
    initAutoRefresh();
    initRealtimeUpdates();
    
    // Анимация загрузки
    setTimeout(() => {
        document.body.classList.add('loaded');
    }, 100);
    
    // Очистка кэша каждые 10 минут
    setInterval(clearExpiredCache, 10 * 60 * 1000);
    
    // Показываем информацию о производительности в консоли
    console.log('🚀 Веб-панель оптимизирована для быстрой работы');
    console.log('💾 Кэширование данных пользователей включено');
    console.log('⚡ Поповеры ограничены для лучшей производительности');
});

// Инициализация тултипов Bootstrap
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Инициализация модальных окон
function initModals() {
    const modalTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="modal"]'));
    modalTriggerList.map(function (modalTriggerEl) {
        return new bootstrap.Modal(modalTriggerEl);
    });
}

// Инициализация popover'ов для пользователей (оптимизированная версия)
function initUserPopovers() {
    // Уничтожаем существующие popover'ы для предотвращения утечек памяти
    const existingPopovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    existingPopovers.forEach(el => {
        const popover = bootstrap.Popover.getInstance(el);
        if (popover) {
            popover.dispose();
        }
    });

    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    
    // Ограничиваем количество одновременно инициализируемых popover'ов
    const maxPopovers = 50;
    const limitedList = popoverTriggerList.slice(0, maxPopovers);
    
    limitedList.forEach(function (popoverTriggerEl) {
        try {
            const popover = new bootstrap.Popover(popoverTriggerEl, {
                trigger: 'hover',
                html: true,
                placement: 'top',
                delay: { show: 300, hide: 100 } // Добавляем задержку для лучшего UX
            });
            
            // Добавляем обработчик клика для показа подробной информации
            popoverTriggerEl.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const userId = this.getAttribute('data-user-id');
                const username = this.getAttribute('data-username');
                
                if (userId && username) {
                    showUserDetails(userId, username);
                } else {
                    showNotification('Ошибка: не удалось получить данные пользователя', 'error');
                }
            });
        } catch (error) {
            console.warn('Ошибка инициализации popover:', error);
        }
    });
    
    // Если есть больше popover'ов, чем лимит, показываем предупреждение
    if (popoverTriggerList.length > maxPopovers) {
        console.warn(`Инициализировано ${limitedList.length} из ${popoverTriggerList.length} popover'ов для оптимизации производительности`);
    }
}

// Показать подробную информацию о пользователе
function showUserDetails(userId, username) {
    // Удаляем существующее модальное окно если есть
    const existingModal = document.getElementById('userDetailsModal');
    if (existingModal) {
        const existingBootstrapModal = bootstrap.Modal.getInstance(existingModal);
        if (existingBootstrapModal) {
            existingBootstrapModal.dispose();
        }
        existingModal.remove();
    }
    
    // Создаем модальное окно с подробной информацией
    const modalHtml = `
        <div class="modal fade" id="userDetailsModal" tabindex="-1" aria-labelledby="userDetailsModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="userDetailsModalLabel">
                            <i class="fas fa-user-circle me-2"></i>Профиль пользователя
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-4 text-center">
                                <div class="user-avatar-large mb-3">
                                    <i class="fas fa-user-circle fa-5x text-primary"></i>
                                </div>
                                <h5>${username}</h5>
                                <p class="text-muted">ID: ${userId}</p>
                            </div>
                            <div class="col-md-8">
                                <div id="userDetailsContent">
                                    <div class="text-center">
                                        <div class="spinner-border text-primary" role="status">
                                            <span class="visually-hidden">Загрузка...</span>
                                        </div>
                                        <p class="mt-2">Загрузка информации о пользователе...</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
                        <button type="button" class="btn btn-primary" onclick="openSendMessageModal(${userId})">
                            <i class="fas fa-paper-plane me-1"></i>Отправить сообщение
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Добавляем новое модальное окно
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Получаем элемент модального окна
    const modalElement = document.getElementById('userDetailsModal');
    
    // Добавляем обработчики событий для кнопок закрытия
    const closeButtons = modalElement.querySelectorAll('[data-bs-dismiss="modal"]');
    closeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
        });
    });
    
    // Добавляем обработчик события скрытия модального окна
    modalElement.addEventListener('hidden.bs.modal', function() {
        // Очищаем кэш для этого пользователя при закрытии модального окна
        clearUserCache(userId);
        // Удаляем модальное окно из DOM
        setTimeout(() => {
            if (modalElement && modalElement.parentNode) {
                modalElement.remove();
            }
        }, 100);
    });
    
    // Показываем модальное окно
    const modal = new bootstrap.Modal(modalElement, {
        backdrop: 'static',
        keyboard: true
    });
    modal.show();
    
    // Загружаем информацию о пользователе
    loadUserDetails(userId);
}

// Простой кэш для данных пользователей
const userCache = new Map();
const CACHE_DURATION = 5 * 60 * 1000; // 5 минут

// Очистка устаревших записей кэша
function clearExpiredCache() {
    const now = Date.now();
    for (const [key, value] of userCache.entries()) {
        if (now - value.timestamp > CACHE_DURATION) {
            userCache.delete(key);
        }
    }
}

// Очистка кэша для конкретного пользователя
function clearUserCache(userId) {
    userCache.delete(userId);
}

// Очистка всего кэша
function clearAllUserCache() {
    userCache.clear();
}

// Мониторинг производительности
const performanceMetrics = {
    cacheHits: 0,
    cacheMisses: 0,
    averageLoadTime: 0,
    totalLoads: 0
};

function updatePerformanceMetrics(loadTime, isCacheHit = false) {
    if (isCacheHit) {
        performanceMetrics.cacheHits++;
    } else {
        performanceMetrics.cacheMisses++;
    }
    
    performanceMetrics.totalLoads++;
    performanceMetrics.averageLoadTime = 
        (performanceMetrics.averageLoadTime * (performanceMetrics.totalLoads - 1) + loadTime) / performanceMetrics.totalLoads;
    
    // Логируем метрики каждые 10 загрузок
    if (performanceMetrics.totalLoads % 10 === 0) {
        console.log(`📊 Метрики производительности:`, {
            'Кэш-попадания': performanceMetrics.cacheHits,
            'Кэш-промахи': performanceMetrics.cacheMisses,
            'Среднее время загрузки': `${performanceMetrics.averageLoadTime.toFixed(2)}ms`,
            'Размер кэша': userCache.size
        });
    }
}

// Загрузка подробной информации о пользователе (оптимизированная версия)
function loadUserDetails(userId) {
    const startTime = Date.now();
    
    // Проверяем кэш
    const cached = userCache.get(userId);
    if (cached && (Date.now() - cached.timestamp) < CACHE_DURATION) {
        displayUserDetails(cached.data);
        updatePerformanceMetrics(Date.now() - startTime, true);
        return;
    }

    // Показываем индикатор загрузки
    const contentDiv = document.getElementById('userDetailsContent');
    if (!contentDiv) {
        console.error('Элемент userDetailsContent не найден');
        return;
    }
    
    contentDiv.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Загрузка...</span>
            </div>
            <p class="mt-2 text-muted">Загрузка информации о пользователе...</p>
        </div>
    `;

    // Добавляем таймаут для предотвращения зависания
    const timeoutId = setTimeout(() => {
        if (contentDiv) {
            contentDiv.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-clock me-2"></i>
                    Загрузка занимает больше времени, чем ожидалось...
                </div>
            `;
        }
        updatePerformanceMetrics(Date.now() - startTime, false);
    }, 5000); // Увеличиваем таймаут до 5 секунд

    fetch(`/api/users/${userId}`)
        .then(response => {
            clearTimeout(timeoutId);
            console.log(`Ответ сервера для пользователя ${userId}:`, response.status, response.statusText);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log(`Данные для пользователя ${userId}:`, data);
            
            if (data.success && data.user) {
                const user = data.user;
                
                // Проверяем корректность данных
                const isValidData = user.id && user.username && user.role !== undefined;
                if (!isValidData) {
                    console.error('Некорректные данные пользователя:', user);
                    throw new Error('Получены некорректные данные о пользователе');
                }

                // Сохраняем в кэш
                userCache.set(userId, {
                    data: user,
                    timestamp: Date.now()
                });

                // Отображаем данные
                displayUserDetails(user);
                updatePerformanceMetrics(Date.now() - startTime, false);
                
            } else {
                console.error('Ошибка в ответе сервера:', data);
                if (contentDiv) {
                    contentDiv.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            <strong>Не удалось загрузить информацию о пользователе:</strong><br>
                            ${data.message || 'Неизвестная ошибка'}<br>
                            <small class="text-muted">Попробуйте обновить страницу</small>
                        </div>
                    `;
                }
                updatePerformanceMetrics(Date.now() - startTime, false);
            }
        })
        .catch(error => {
            clearTimeout(timeoutId);
            console.error(`Ошибка загрузки информации о пользователе ${userId}:`, error);
            
            if (contentDiv) {
                contentDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-times-circle me-2"></i>
                        <strong>Ошибка загрузки данных:</strong><br>
                        ${error.message}<br>
                        <small class="text-muted">Попробуйте обновить страницу или обратитесь к администратору</small>
                        <br><br>
                        <button class="btn btn-sm btn-outline-primary" onclick="loadUserDetails(${userId})">
                            <i class="fas fa-redo me-1"></i>Повторить попытку
                        </button>
                    </div>
                `;
            }
            updatePerformanceMetrics(Date.now() - startTime, false);
        });
}

// Вспомогательные функции для улучшения отображения
function getRoleBadgeColor(role) {
    switch(role) {
        case 'main_admin': return 'danger';
        case 'admin': return 'warning';
        case 'user': return 'secondary';
        default: return 'secondary';
    }
}

function getRoleDisplayName(role) {
    switch(role) {
        case 'main_admin': return 'Boss';
        case 'admin': return 'Admin';
        case 'user': return 'Пользователь';
        default: return 'Пользователь';
    }
}

function getActivityColor(score) {
    if (score >= 80) return 'success';
    if (score >= 60) return 'info';
    if (score >= 40) return 'warning';
    return 'danger';
}

// Отображение данных пользователя
function displayUserDetails(user) {
    const contentDiv = document.getElementById('userDetailsContent');
    
    const content = `
        <div class="user-stats">
            <div class="row">
                <div class="col-md-6">
                    <div class="stat-card mb-3">
                        <div class="stat-card-header">
                            <i class="fas fa-calendar-alt text-info"></i>
                            <span>Дата регистрации</span>
                        </div>
                        <div class="stat-card-value">${formatDate(user.created_at)}</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="stat-card mb-3">
                        <div class="stat-card-header">
                            <i class="fas fa-clock text-warning"></i>
                            <span>Последняя активность</span>
                        </div>
                        <div class="stat-card-value">${formatDate(user.last_activity)}</div>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <div class="stat-card mb-3">
                        <div class="stat-card-header">
                            <i class="fas fa-star text-success"></i>
                            <span>Роль</span>
                        </div>
                        <div class="stat-card-value">
                            <span class="badge bg-${getRoleBadgeColor(user.role)}">
                                ${getRoleDisplayName(user.role)}
                            </span>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="stat-card mb-3">
                        <div class="stat-card-header">
                            <i class="fas fa-users text-primary"></i>
                            <span>Рефералы</span>
                        </div>
                        <div class="stat-card-value">${user.referral_count || 0}</div>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <div class="stat-card mb-3">
                        <div class="stat-card-header">
                            <i class="fas fa-toggle-on text-${user.is_active ? 'success' : 'danger'}"></i>
                            <span>Статус</span>
                        </div>
                        <div class="stat-card-value">
                            <span class="badge bg-${user.is_active ? 'success' : 'danger'}">
                                ${user.is_active ? 'Активен' : 'Заблокирован'}
                            </span>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="stat-card mb-3">
                        <div class="stat-card-header">
                            <i class="fas fa-chart-line text-info"></i>
                            <span>Активность</span>
                        </div>
                        <div class="stat-card-value">
                            <div class="d-flex align-items-center">
                                <span class="me-2">${user.activity_score || 0}%</span>
                                <div class="progress flex-grow-1" style="height: 6px;">
                                    <div class="progress-bar bg-${getActivityColor(user.activity_score)}" 
                                         style="width: ${user.activity_score || 0}%"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <div class="stat-card mb-3">
                        <div class="stat-card-header">
                            <i class="fas fa-sticky-note text-warning"></i>
                            <span>Заметки</span>
                        </div>
                        <div class="stat-card-value">${user.notes_count || 0}</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="stat-card mb-3">
                        <div class="stat-card-header">
                            <i class="fas fa-user-plus text-info"></i>
                            <span>Реферер</span>
                        </div>
                        <div class="stat-card-value">
                            ${user.referrer_username ? `<span class="text-primary">${user.referrer_username}</span>` : '<span class="text-muted">Нет</span>'}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    contentDiv.innerHTML = content;
    
    // Добавляем анимацию появления
    setTimeout(() => {
        const cards = contentDiv.querySelectorAll('.stat-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            setTimeout(() => {
                card.style.transition = 'all 0.3s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }, 100);
}

// Инициализация поиска
function initSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            performSearch(this.value);
        }, 300));
    }
}

// Инициализация автообновления
function initAutoRefresh() {
    // Автообновление каждые 30 секунд на dashboard
    if (window.location.pathname === '/dashboard') {
        refreshInterval = setInterval(function() {
            updateDashboardStats();
        }, 30000);
    }
}

// Инициализация real-time обновлений
function initRealtimeUpdates() {
    // Real-time обновления каждые 5 секунд на dashboard
    if (window.location.pathname === '/dashboard') {
        let updateCounter = 0;
        realtimeStatsInterval = setInterval(function() {
            updateRealtimeStats();
            
            // Обновляем popover'ы только каждые 3 обновления (15 секунд) для оптимизации
            updateCounter++;
            if (updateCounter % 3 === 0) {
                setTimeout(initUserPopovers, 1000);
            }
        }, 5000);
    }
}

// Инициализация темы
function initTheme() {
    document.documentElement.setAttribute('data-theme', currentTheme);
    document.body.classList.add('theme-transition');
}

// Переключение темы
function toggleTheme() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    localStorage.setItem('theme', currentTheme);
    updateThemeIcon();
    
    // Обновляем графики если они есть
    if (typeof updateCharts === 'function') {
        updateCharts(currentPeriod);
    }
    
    // Показываем уведомление
    showNotification(`Переключена на ${currentTheme === 'dark' ? 'темную' : 'светлую'} тему`, 'info');
}

// Обновление иконки темы
function updateThemeIcon() {
    const themeIcon = document.getElementById('themeIcon');
    const themeToggle = document.getElementById('themeToggle');
    
    if (themeIcon && themeToggle) {
        if (currentTheme === 'dark') {
            themeIcon.className = 'fas fa-sun';
            themeToggle.title = 'Переключить на светлую тему';
        } else {
            themeIcon.className = 'fas fa-moon';
            themeToggle.title = 'Переключить на темную тему';
        }
    }
}

// Функция debounce для оптимизации поиска
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Выполнение поиска
function performSearch(query) {
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.set('search', query);
    currentUrl.searchParams.set('page', '1');
    window.location.href = currentUrl.toString();
}

// Обновление статистики dashboard
function updateDashboardStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            updateStatsCards(data);
        })
        .catch(error => {
            console.error('Ошибка обновления статистики:', error);
        });
}

// Обновление real-time статистики
function updateRealtimeStats() {
    fetch('/api/realtime/stats')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Ошибка real-time статистики:', data.error);
                return;
            }
            
            // Обновляем статистику пользователей
            updateUserStats(data.users);
            
            // Обновляем статистику событий
            updateEventStats(data.events);
            
            // Обновляем статистику рефералов
            updateReferralStats(data.referrals);
            
            // Обновляем информацию о боте
            updateBotInfo(data.bot);
            
            // Обновляем timestamp
            updateLastUpdate(data.timestamp);
        })
        .catch(error => {
            console.error('Ошибка обновления real-time статистики:', error);
        });
}

// Обновление статистики пользователей
function updateUserStats(users) {
    const elements = {
        'total-users': users.total,
        'regular-users': users.regular,
        'admin-users': users.admin,
        'boss-users': users.boss
    };
    
    for (const [id, value] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value || 0;
        }
    }
}

// Обновление статистики событий
function updateEventStats(events) {
    const elements = {
        'total-events': events.total,
        'events-24h': events.last_24h
    };
    
    for (const [id, value] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value || 0;
        }
    }
}

// Обновление статистики рефералов
function updateReferralStats(referrals) {
    const elements = {
        'total-referrals': referrals.total,
        'unique-referrers': referrals.unique_referrers
    };
    
    for (const [id, value] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value || 0;
        }
    }
}

// Обновление информации о боте
function updateBotInfo(bot) {
    // Обновляем статус бота
    const statusElement = document.querySelector('.badge.bg-success, .badge.bg-danger');
    if (statusElement && bot.status) {
        const isOnline = bot.status === 'running';
        statusElement.className = `badge bg-${isOnline ? 'success' : 'danger'} fs-6`;
        statusElement.innerHTML = `<i class="fas fa-circle"></i> ${isOnline ? 'Онлайн' : 'Офлайн'}`;
    }
    
    // Обновляем uptime
    const uptimeElement = document.getElementById('bot-uptime');
    if (uptimeElement && bot.uptime) {
        uptimeElement.textContent = bot.uptime;
    }
}

// Обновление времени последнего обновления
function updateLastUpdate(timestamp) {
    const lastUpdateElement = document.getElementById('last-update');
    if (lastUpdateElement && timestamp) {
        const date = new Date(timestamp);
        lastUpdateElement.textContent = date.toLocaleTimeString('ru-RU');
    }
}

// Обновление карточек статистики
function updateStatsCards(stats) {
    // Обновляем карточки статистики
    const cards = {
        'total-users': stats.total_users,
        'regular-users': stats.regular_users,
        'admin-users': stats.admin_users,
        'boss-users': stats.boss_users,
        'total-events': stats.total_events,
        'events-24h': stats.events_24h,
        'total-referrals': stats.total_referrals,
        'unique-referrers': stats.unique_referrers
    };
    
    for (const [id, value] of Object.entries(cards)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value || 0;
        }
    }
}

// Управление ботом
function controlBot(action) {
    const button = event.target;
    const originalText = button.innerHTML;
    
    // Показываем индикатор загрузки
    button.innerHTML = '<span class="loading"></span> Загрузка...';
    button.disabled = true;
    
    fetch('/api/bot/status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({action: action})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message || 'Бот успешно ' + (action === 'start' ? 'запущен' : 'остановлен'), 'success');
            
            // Обновляем статус бота
            updateBotStatus(data.status);
            
            // Обновляем статистику через 2 секунды
            setTimeout(() => {
                updateRealtimeStats();
            }, 2000);
        } else {
            showNotification(data.message || 'Ошибка при управлении ботом', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Ошибка при управлении ботом', 'error');
    })
    .finally(() => {
        // Восстанавливаем кнопку
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// Обновление статуса бота
function updateBotStatus(status) {
    const statusElement = document.querySelector('.badge.bg-success, .badge.bg-danger');
    if (statusElement) {
        const isOnline = status === 'running';
        statusElement.className = `badge bg-${isOnline ? 'success' : 'danger'} fs-6`;
        statusElement.innerHTML = `<i class="fas fa-circle"></i> ${isOnline ? 'Онлайн' : 'Офлайн'}`;
    }
}

// Отправка сообщения пользователю
function sendMessageToUser(userId, message) {
    if (!userId || !message) {
        showNotification('Введите ID пользователя и сообщение', 'warning');
        return;
    }
    
    fetch('/api/bot/send-message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_id: parseInt(userId),
            message: message
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Сообщение отправлено', 'success');
        } else {
            showNotification(data.message || 'Ошибка отправки сообщения', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Ошибка отправки сообщения', 'error');
    });
}

// Открытие модального окна для отправки сообщения
function openSendMessageModal(userId = null) {
    // Закрываем модальное окно с профилем пользователя если оно открыто
    const userDetailsModal = document.getElementById('userDetailsModal');
    if (userDetailsModal) {
        const modal = bootstrap.Modal.getInstance(userDetailsModal);
        if (modal) {
            modal.hide();
        }
    }
    
    // Устанавливаем ID пользователя если передан
    if (userId) {
        document.getElementById('messageUserId').value = userId;
    }
    
    // Показываем модальное окно отправки сообщения
    const sendMessageModal = new bootstrap.Modal(document.getElementById('sendMessageModal'));
    sendMessageModal.show();
}

// Установка моего ID в поле отправки сообщения
function setMyId() {
    fetch('/api/user/current')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('messageUserId').value = data.user_id;
                showNotification('Установлен ваш ID', 'success');
            } else {
                showNotification('Не удалось получить ваш ID', 'error');
            }
        })
        .catch(error => {
            console.error('Ошибка получения ID:', error);
            showNotification('Ошибка получения ID', 'error');
        });
}

// Отправка сообщения всем пользователям
function sendToAll() {
    document.getElementById('messageUserId').value = 'all';
    showNotification('Сообщение будет отправлено всем пользователям', 'info');
}

// Отправка сообщения (основная функция)
function sendMessage() {
    const userId = document.getElementById('messageUserId').value;
    const message = document.getElementById('messageText').value;
    
    if (!message.trim()) {
        showNotification('Введите текст сообщения', 'warning');
        return;
    }
    
    if (userId === 'all') {
        // Отправка всем пользователям
        fetch('/api/bot/send-message-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Сообщение отправлено всем пользователям', 'success');
                // Закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('sendMessageModal'));
                modal.hide();
                // Очищаем поля
                document.getElementById('messageText').value = '';
                document.getElementById('messageUserId').value = '';
            } else {
                showNotification(data.message || 'Ошибка отправки сообщения', 'error');
            }
        })
        .catch(error => {
            console.error('Ошибка отправки сообщения:', error);
            showNotification('Ошибка отправки сообщения', 'error');
        });
    } else {
        // Отправка конкретному пользователю
        sendMessageToUser(userId, message);
        // Закрываем модальное окно
        const modal = bootstrap.Modal.getInstance(document.getElementById('sendMessageModal'));
        modal.hide();
        // Очищаем поля
        document.getElementById('messageText').value = '';
        document.getElementById('messageUserId').value = '';
    }
}

// Функция для показа уведомлений
function showNotification(message, type = 'info') {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Добавляем на страницу
    document.body.appendChild(notification);
    
    // Автоматически скрываем через 3 секунды
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// Экспорт данных
function exportData(type) {
    const button = event.target;
    const originalText = button.innerHTML;
    
    button.innerHTML = '<span class="loading"></span> Экспорт...';
    button.disabled = true;
    
    // Здесь будет логика экспорта
    setTimeout(() => {
        showNotification('Экспорт данных начат', 'info');
        button.innerHTML = originalText;
        button.disabled = false;
    }, 2000);
}

// Фильтрация таблиц
function filterTable(tableId, column, value) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    
    for (let row of rows) {
        const cell = row.getElementsByTagName('td')[column];
        if (cell) {
            const text = cell.textContent || cell.innerText;
            if (text.toLowerCase().includes(value.toLowerCase())) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        }
    }
}

// Сортировка таблиц
function sortTable(tableId, column) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.getElementsByTagName('tbody')[0];
    const rows = Array.from(tbody.getElementsByTagName('tr'));
    
    rows.sort((a, b) => {
        const aText = a.getElementsByTagName('td')[column].textContent;
        const bText = b.getElementsByTagName('td')[column].textContent;
        return aText.localeCompare(bText);
    });
    
    // Перестраиваем таблицу
    rows.forEach(row => tbody.appendChild(row));
}

// Анимация появления элементов
function addFadeInAnimation() {
    const elements = document.querySelectorAll('.card, .table');
    elements.forEach((element, index) => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            element.style.transition = 'all 0.5s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// Очистка при уходе со страницы
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    if (realtimeStatsInterval) {
        clearInterval(realtimeStatsInterval);
    }
});

// Обработка ошибок
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    showNotification('Произошла ошибка на странице', 'error');
});

// Утилиты для работы с датами
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Утилиты для работы с числами
function formatNumber(num) {
    return new Intl.NumberFormat('ru-RU').format(num);
}

// Проверка подключения к интернету
function checkConnection() {
    if (!navigator.onLine) {
        showNotification('Нет подключения к интернету', 'warning');
    }
}

window.addEventListener('online', function() {
    showNotification('Подключение восстановлено', 'success');
});

window.addEventListener('offline', function() {
    showNotification('Нет подключения к интернету', 'warning');
}); 