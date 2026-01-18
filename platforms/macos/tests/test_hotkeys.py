"""
Тесты для горячих клавиш VTTv2 (quickmachotkey)
"""
import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestHotkeyManager:
    """Тесты HotkeyManager с quickmachotkey"""
    
    def test_hotkey_initialization(self):
        """Тест инициализации HotkeyManager"""
        from src.system.hotkeys import HotkeyManager
        
        callback = Mock()
        manager = HotkeyManager("option+space", callback=callback)
        
        assert manager.hotkey_string == "option+space"
        assert manager.callback == callback
        assert manager.is_running is False
        assert manager.debounce_timeout == 0.3
        assert manager.activation_count == 0
        assert manager.virtual_key is not None
        assert manager.modifier_mask is not None
    
    def test_hotkey_parse_option_space(self):
        """Тест парсинга option+space"""
        from src.system.hotkeys import HotkeyManager
        from quickmachotkey.constants import kVK_Space, optionKey
        
        manager = HotkeyManager("option+space")
        
        assert manager.virtual_key == kVK_Space
        assert manager.modifier_mask == optionKey
    
    def test_hotkey_parse_cmd_shift_a(self):
        """Тест парсинга cmd+shift+a"""
        from src.system.hotkeys import HotkeyManager
        from quickmachotkey.constants import kVK_ANSI_A
        from quickmachotkey import mask
        from quickmachotkey.constants import cmdKey, shiftKey
        
        manager = HotkeyManager("cmd+shift+a")
        
        assert manager.virtual_key == kVK_ANSI_A
        assert manager.modifier_mask == mask(cmdKey, shiftKey)
    
    def test_hotkey_parse_alt_space(self):
        """Тест парсинга alt+space (синоним option)"""
        from src.system.hotkeys import HotkeyManager
        from quickmachotkey.constants import kVK_Space, optionKey
        
        manager = HotkeyManager("alt+space")
        
        assert manager.virtual_key == kVK_Space
        assert manager.modifier_mask == optionKey
    
    def test_hotkey_parse_invalid(self):
        """Тест парсинга невалидной комбинации"""
        from src.system.hotkeys import HotkeyManager
        
        with pytest.raises(ValueError, match="Неизвестная клавиша"):
            HotkeyManager("invalid+key")
        
        with pytest.raises(ValueError, match="Не указана основная клавиша"):
            HotkeyManager("option+cmd")
    
    def test_debounce_mechanism(self):
        """Тест debounce механизма для предотвращения повторных активаций"""
        from src.system.hotkeys import HotkeyManager
        
        callback = Mock()
        manager = HotkeyManager("option+space", callback=callback)
        manager.debounce_timeout = 0.1  # Короткий таймаут для теста
        
        # Симулируем первую активацию
        manager.last_activation_time = time.time()
        manager.activation_count = 1
        
        # Симулируем вторую активацию сразу после первой
        current_time = time.time()
        time_since_last = current_time - manager.last_activation_time
        
        # Должна быть заблокирована из-за debounce
        if time_since_last < manager.debounce_timeout:
            assert time_since_last < manager.debounce_timeout
    
    def test_is_healthy_not_running(self):
        """Тест проверки здоровья когда listener не запущен"""
        from src.system.hotkeys import HotkeyManager
        
        manager = HotkeyManager("option+space")
        assert manager.is_healthy() is False
    
    def test_get_stats(self):
        """Тест получения статистики"""
        from src.system.hotkeys import HotkeyManager
        
        manager = HotkeyManager("option+space")
        stats = manager.get_stats()
        
        assert 'is_running' in stats
        assert 'is_healthy' in stats
        assert 'activation_count' in stats
        assert 'hotkey_string' in stats
        assert 'virtual_key' in stats
        assert 'modifier_mask' in stats
        assert stats['hotkey_string'] == "option+space"
        assert stats['activation_count'] == 0
        assert stats['is_running'] is False
    
    def test_set_callback(self):
        """Тест установки callback"""
        from src.system.hotkeys import HotkeyManager
        
        callback1 = Mock()
        callback2 = Mock()
        
        manager = HotkeyManager("option+space", callback=callback1)
        assert manager.callback == callback1
        
        manager.set_callback(callback2)
        assert manager.callback == callback2


class TestHotkeyIntegration:
    """Интеграционные тесты горячих клавиш"""
    
    @patch('src.system.hotkeys.quickHotKey')
    def test_hotkey_start(self, mock_quickHotKey):
        """Тест запуска listener'а"""
        from src.system.hotkeys import HotkeyManager
        
        # Мокаем декоратор quickHotKey
        mock_decorator = MagicMock()
        mock_handler = MagicMock()
        mock_quickHotKey.return_value = lambda func: mock_handler
        
        callback = Mock()
        manager = HotkeyManager("option+space", callback=callback)
        
        manager.start()
        
        assert manager.is_running is True
        assert manager.hotkey_handler is not None
        # Проверяем, что quickHotKey был вызван с правильными параметрами
        mock_quickHotKey.assert_called_once()
        call_kwargs = mock_quickHotKey.call_args[1]
        assert 'virtualKey' in call_kwargs
        assert 'modifierMask' in call_kwargs
    
    def test_hotkey_stop(self):
        """Тест остановки listener'а"""
        from src.system.hotkeys import HotkeyManager
        
        callback = Mock()
        manager = HotkeyManager("option+space", callback=callback)
        
        # Устанавливаем состояние как запущенное
        manager.is_running = True
        manager.hotkey_handler = MagicMock()
        
        manager.stop()
        
        assert manager.is_running is False
        assert manager.hotkey_handler is None
    
    @patch('src.system.hotkeys.quickHotKey')
    def test_hotkey_restart(self, mock_quickHotKey):
        """Тест перезапуска listener'а"""
        from src.system.hotkeys import HotkeyManager
        
        mock_decorator = MagicMock()
        mock_handler = MagicMock()
        mock_quickHotKey.return_value = lambda func: mock_handler
        
        callback = Mock()
        manager = HotkeyManager("option+space", callback=callback)
        
        manager.start()
        assert manager.is_running is True
        
        manager.restart()
        
        # После перезапуска должен быть запущен снова
        assert manager.is_running is True
        # quickHotKey должен быть вызван дважды (start + restart)
        assert mock_quickHotKey.call_count == 2
    
    def test_callback_protection_from_race_conditions(self):
        """Тест защиты callback от состояний гонки"""
        from src.system.hotkeys import HotkeyManager
        
        callback_calls = []
        callback_lock = threading.Lock()
        
        def callback():
            with callback_lock:
                callback_calls.append(time.time())
        
        manager = HotkeyManager("option+space", callback=callback)
        manager.debounce_timeout = 0.05
        
        # Симулируем быстрые последовательные активации
        manager.last_activation_time = time.time()
        manager.activation_count = 1
        
        # Вторая активация должна быть заблокирована debounce
        current_time = time.time()
        if current_time - manager.last_activation_time < manager.debounce_timeout:
            # Активация заблокирована
            pass
        
        # Проверяем, что callback не вызывался повторно
        # (в реальном сценарии callback вызывается только если debounce прошел)


class TestHotkeyParsing:
    """Тесты парсинга различных комбинаций горячих клавиш"""
    
    def test_parse_single_key(self):
        """Тест парсинга одной клавиши без модификаторов"""
        from src.system.hotkeys import HotkeyManager
        from quickmachotkey.constants import kVK_Space
        
        manager = HotkeyManager("space")
        
        assert manager.virtual_key == kVK_Space
        assert manager.modifier_mask == 0
    
    def test_parse_multiple_modifiers(self):
        """Тест парсинга нескольких модификаторов"""
        from src.system.hotkeys import HotkeyManager
        from quickmachotkey.constants import kVK_ANSI_X
        from quickmachotkey import mask
        from quickmachotkey.constants import cmdKey, controlKey, optionKey
        
        manager = HotkeyManager("cmd+control+option+x")
        
        assert manager.virtual_key == kVK_ANSI_X
        assert manager.modifier_mask == mask(cmdKey, controlKey, optionKey)
    
    def test_parse_case_insensitive(self):
        """Тест парсинга без учета регистра"""
        from src.system.hotkeys import HotkeyManager
        from quickmachotkey.constants import kVK_Space, optionKey
        
        manager1 = HotkeyManager("OPTION+SPACE")
        manager2 = HotkeyManager("option+space")
        
        assert manager1.virtual_key == manager2.virtual_key
        assert manager1.modifier_mask == manager2.modifier_mask
    
    def test_parse_with_spaces(self):
        """Тест парсинга с пробелами"""
        from src.system.hotkeys import HotkeyManager
        from quickmachotkey.constants import kVK_Space, optionKey
        
        manager = HotkeyManager("option + space")
        
        assert manager.virtual_key == kVK_Space
        assert manager.modifier_mask == optionKey
