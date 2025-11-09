"""
Тесты для системных разрешений macOS (с моками)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPermissionsChecker:
    """Тесты проверки разрешений macOS"""
    
    @patch('AVFoundation.AVAudioSession')
    def test_microphone_permission_granted(self, mock_av_session_class):
        """Тест проверки разрешения на микрофон (предоставлено)"""
        from src.system.permissions import PermissionsChecker
        
        # Мокируем AVAudioSession
        mock_session = MagicMock()
        mock_session.recordPermission.return_value = 1735552628  # Granted
        mock_av_session_class.sharedInstance.return_value = mock_session
        
        checker = PermissionsChecker()
        result = checker.check_microphone_permission(fail_fast=False)
        
        assert result is True
    
    @patch('AVFoundation.AVAudioSession')
    def test_microphone_permission_denied(self, mock_av_session_class):
        """Тест проверки разрешения на микрофон (отклонено)"""
        from src.system.permissions import PermissionsChecker
        
        mock_session = MagicMock()
        mock_session.recordPermission.return_value = 1735552629  # Denied
        mock_av_session_class.sharedInstance.return_value = mock_session
        
        checker = PermissionsChecker()
        result = checker.check_microphone_permission(fail_fast=False)
        
        assert result is False
    
    @patch('src.system.permissions.CGEventSourceKeyState')
    def test_accessibility_permission_granted(self, mock_cg_event):
        """Тест проверки разрешения Accessibility (предоставлено)"""
        from src.system.permissions import PermissionsChecker
        
        # Мокируем CGEventSourceKeyState - если работает без ошибки, разрешение есть
        mock_cg_event.return_value = True
        
        checker = PermissionsChecker()
        result = checker.check_accessibility_permission(fail_fast=False)
        
        assert result is True
    
    @patch('src.system.permissions.CGEventSourceKeyState')
    def test_accessibility_permission_denied(self, mock_cg_event):
        """Тест проверки разрешения Accessibility (отклонено)"""
        from src.system.permissions import PermissionsChecker
        
        # Мокируем CGEventSourceKeyState - если выбросит исключение, разрешения нет
        mock_cg_event.side_effect = Exception("Accessibility permission denied")
        
        checker = PermissionsChecker()
        result = checker.check_accessibility_permission(fail_fast=False)
        
        assert result is False
    
    @patch('AVFoundation.AVAudioSession')
    def test_microphone_permission_fail_fast(self, mock_av_session_class):
        """Тест fail_fast режима для микрофона"""
        from src.system.permissions import PermissionsChecker
        
        mock_session = MagicMock()
        mock_session.recordPermission.return_value = 1735552629  # Denied
        mock_av_session_class.sharedInstance.return_value = mock_session
        
        checker = PermissionsChecker()
        
        # Должно выбросить SystemExit при fail_fast=True
        with pytest.raises(SystemExit):
            checker.check_microphone_permission(fail_fast=True)


