"""
Test cases for Monitor Components
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.monitor.stats_panel import StatsPanel
from src.monitor.log_viewer import LogViewer
from src.monitor.monitor_window import MonitorWindow
from src.monitor.theme_styles import ThemeStyles


class TestStatsPanel:
    """Test cases for StatsPanel"""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock AnimationEngine"""
        engine = Mock()
        engine.get_stats = Mock()
        return engine
    
    def test_stats_panel_initialization(self, mock_engine):
        """Test initialization of StatsPanel"""
        with patch('tkinter.Frame'):
            panel = StatsPanel(None, mock_engine)
            assert panel.engine == mock_engine
            assert panel.stats_vars is not None
    
    def test_update_stats(self, mock_engine):
        """Test update stats"""
        mock_stats = Mock()
        mock_stats.total_leds = 225
        mock_stats.active_leds = 100
        mock_stats.frame_count = 1000
        mock_stats.actual_fps = 60.0
        mock_stats.animation_time = 1.5
        mock_stats.master_brightness = 255
        mock_stats.speed_percent = 100.0
        
        mock_engine.get_stats.return_value = mock_stats
        
        with patch('tkinter.Frame'), patch('tkinter.StringVar') as mock_var:
            panel = StatsPanel(None, mock_engine)
            panel.stats_vars = {
                'total_leds': mock_var(),
                'active_leds': mock_var(),
                'frame_count': mock_var(),
                'fps': mock_var(),
                'animation_time': mock_var(),
                'brightness': mock_var(),
                'speed': mock_var()
            }
            
            panel.update_stats()
            
            mock_engine.get_stats.assert_called_once()
            
            for var in panel.stats_vars.values():
                var.set.assert_called()


class TestLogViewer:
    """Test cases for LogViewer"""
    
    def test_log_viewer_initialization(self):
        """Test initialization of LogViewer"""
        with patch('tkinter.Frame'), patch('tkinter.Text') as mock_text:
            viewer = LogViewer(None)
            assert viewer.max_lines == 1000
            mock_text.assert_called()
    
    def test_add_log(self):
        """Test adding a log entry"""
        with patch('tkinter.Frame'), patch('tkinter.Text') as mock_text:
            mock_text_widget = Mock()
            mock_text.return_value = mock_text_widget
            
            viewer = LogViewer(None)
            viewer.text_widget = mock_text_widget
            
            test_message = "Test log message"
            viewer.add_log("INFO", test_message)
            
            mock_text_widget.insert.assert_called()
            mock_text_widget.see.assert_called()
    
    def test_clear_logs(self):
        """Test xóa logs"""
        with patch('tkinter.Frame'), patch('tkinter.Text') as mock_text:
            mock_text_widget = Mock()
            mock_text.return_value = mock_text_widget
            
            viewer = LogViewer(None)
            viewer.text_widget = mock_text_widget
            
            viewer.clear_logs()
            
            mock_text_widget.delete.assert_called()
    
    def test_max_lines_limit(self):
        """Test log line limit"""
        with patch('tkinter.Frame'), patch('tkinter.Text') as mock_text:
            mock_text_widget = Mock()
            mock_text_widget.get.return_value = "1.0"
            mock_text_widget.index.return_value = "1001.0" 
            mock_text.return_value = mock_text_widget
            
            viewer = LogViewer(None, max_lines=10)
            viewer.text_widget = mock_text_widget
            
            viewer.add_log("INFO", "Test message")
            
            mock_text_widget.delete.assert_called()


class TestMonitorWindow:
    """Test cases for MonitorWindow"""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock AnimationEngine"""
        engine = Mock()
        engine.get_stats = Mock()
        return engine
    
    def test_monitor_window_initialization(self, mock_engine):
        """Test khởi tạo MonitorWindow"""
        with patch('tkinter.Tk') as mock_tk, \
             patch('src.monitor.stats_panel.StatsPanel') as mock_panel, \
             patch('src.monitor.log_viewer.LogViewer') as mock_viewer:
            
            window = MonitorWindow(mock_engine)
            
            assert window.engine == mock_engine
            mock_tk.assert_called()
            mock_panel.assert_called()
            mock_viewer.assert_called()
    
    def test_start_monitoring(self, mock_engine):
        """Test bắt đầu monitoring"""
        with patch('tkinter.Tk') as mock_tk, \
             patch('src.monitor.stats_panel.StatsPanel'), \
             patch('src.monitor.log_viewer.LogViewer'):
            
            mock_root = Mock()
            mock_tk.return_value = mock_root
            
            window = MonitorWindow(mock_engine)
            window.start()
            
            mock_root.mainloop.assert_called()
    
    def test_update_stats_periodically(self, mock_engine):
        """Test periodic stats update"""
        with patch('tkinter.Tk') as mock_tk, \
             patch('src.monitor.stats_panel.StatsPanel') as mock_panel, \
             patch('src.monitor.log_viewer.LogViewer'):
            
            mock_root = Mock()
            mock_tk.return_value = mock_root
            mock_stats_panel = Mock()
            mock_panel.return_value = mock_stats_panel
            
            window = MonitorWindow(mock_engine)
            window.stats_panel = mock_stats_panel
            
            window.update_display()
            
            mock_stats_panel.update_stats.assert_called_once()
    
    def test_log_message_handling(self, mock_engine):
        """Test xử lý log messages"""
        with patch('tkinter.Tk'), \
             patch('src.monitor.stats_panel.StatsPanel'), \
             patch('src.monitor.log_viewer.LogViewer') as mock_viewer:
            
            mock_log_viewer = Mock()
            mock_viewer.return_value = mock_log_viewer
            
            window = MonitorWindow(mock_engine)
            window.log_viewer = mock_log_viewer
            
            window.add_log("ERROR", "Test error message")
            
            mock_log_viewer.add_log.assert_called_with("ERROR", "Test error message")


class TestThemeStyles:
    """Test cases cho ThemeStyles"""
    
    def test_theme_initialization(self):
        """Test khởi tạo theme"""
        theme = ThemeStyles()
        
        assert hasattr(theme, 'bg_color')
        assert hasattr(theme, 'fg_color')
        assert hasattr(theme, 'accent_color')
        assert hasattr(theme, 'font_family')
        assert hasattr(theme, 'font_size')
    
    def test_get_button_style(self):
        """Test get button style"""
        theme = ThemeStyles()
        button_style = theme.get_button_style()
        
        assert isinstance(button_style, dict)
        assert 'bg' in button_style
        assert 'fg' in button_style
        assert 'font' in button_style
    
    def test_get_label_style(self):
        """Test get label style"""
        theme = ThemeStyles()
        label_style = theme.get_label_style()
        
        assert isinstance(label_style, dict)
        assert 'bg' in label_style
        assert 'fg' in label_style
        assert 'font' in label_style
    
    def test_get_text_style(self):
        """Test get text widget style"""
        theme = ThemeStyles()
        text_style = theme.get_text_style()
        
        assert isinstance(text_style, dict)
        assert 'bg' in text_style
        assert 'fg' in text_style
        assert 'font' in text_style
        assert 'wrap' in text_style
    
    def test_get_frame_style(self):
        """Test get frame style"""
        theme = ThemeStyles()
        frame_style = theme.get_frame_style()
        
        assert isinstance(frame_style, dict)
        assert 'bg' in frame_style
        assert 'relief' in frame_style
        assert 'bd' in frame_style
    
    def test_apply_theme_consistency(self):
        """Test theme consistency across components"""
        theme = ThemeStyles()
        
        button_style = theme.get_button_style()
        label_style = theme.get_label_style()
        text_style = theme.get_text_style()
        frame_style = theme.get_frame_style()
        
        assert button_style['bg'] == theme.accent_color
        assert label_style['bg'] == theme.bg_color
        assert text_style['bg'] == theme.bg_color
        assert frame_style['bg'] == theme.bg_color
        
        assert button_style['fg'] == theme.fg_color
        assert label_style['fg'] == theme.fg_color
        assert text_style['fg'] == theme.fg_color
    
    def test_responsive_layout_settings(self):
        """Test responsive layout settings"""
        theme = ThemeStyles()
        
        grid_settings = theme.get_grid_settings()
        assert isinstance(grid_settings, dict)
        assert 'padx' in grid_settings
        assert 'pady' in grid_settings
        assert 'sticky' in grid_settings
        
        pack_settings = theme.get_pack_settings()
        assert isinstance(pack_settings, dict)
        assert 'padx' in pack_settings
        assert 'pady' in pack_settings
        assert 'fill' in pack_settings


class TestMonitorIntegration:
    """Integration tests cho Monitor components"""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock complete engine"""
        engine = Mock()
        mock_stats = Mock()
        mock_stats.total_leds = 225
        mock_stats.active_leds = 100
        mock_stats.frame_count = 1000
        mock_stats.actual_fps = 60.0
        mock_stats.animation_time = 1.5
        mock_stats.master_brightness = 255
        mock_stats.speed_percent = 100.0
        engine.get_stats.return_value = mock_stats
        return engine
    
    def test_full_monitor_workflow(self, mock_engine):
        """Test complete monitoring workflow"""
        with patch('tkinter.Tk'), \
             patch('tkinter.Frame'), \
             patch('tkinter.Text'), \
             patch('tkinter.Label'), \
             patch('tkinter.StringVar'):
            
            monitor = MonitorWindow(mock_engine)
            
            monitor.update_display()
            
            monitor.add_log("INFO", "Engine started")
            monitor.add_log("WARNING", "High temperature detected")
            monitor.add_log("ERROR", "Connection lost")
            
            mock_engine.get_stats.assert_called()
    
    def test_theme_application(self, mock_engine):
        """Test theme is applied correctly"""
        with patch('tkinter.Tk'), \
             patch('tkinter.Frame'), \
             patch('tkinter.Text'), \
             patch('tkinter.Label'), \
             patch('tkinter.StringVar'):
            
            theme = ThemeStyles()
            monitor = MonitorWindow(mock_engine)
            
            button_style = theme.get_button_style()
            label_style = theme.get_label_style()
            text_style = theme.get_text_style()
            frame_style = theme.get_frame_style()
            
            for style in [button_style, label_style, text_style, frame_style]:
                assert isinstance(style, dict)
                assert len(style) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 