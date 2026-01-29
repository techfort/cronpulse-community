"""
Unit tests for monitor scheduler functionality
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch, call
from api.services.monitor_service import MonitorService
from db.models.monitor import Monitor
from db.models.user import User


class TestMonitorService:
    """Test MonitorService scheduled checking logic"""
    
    @pytest.fixture
    def mock_repos(self):
        """Create mock repositories"""
        monitor_repo = Mock()
        user_repo = Mock()
        settings_repo = Mock()
        settings_repo.get_setting.return_value = None  # No SMTP by default
        return monitor_repo, user_repo, settings_repo
    
    @pytest.fixture
    def monitor_service(self, mock_repos):
        """Create MonitorService with mock repos"""
        monitor_repo, user_repo, settings_repo = mock_repos
        return MonitorService(monitor_repo, user_repo, settings_repo)
    
    def test_check_missed_pings_detects_overdue_monitor(self, monitor_service, mock_repos):
        """Test that check_missed_pings detects an overdue monitor"""
        monitor_repo, _, _ = mock_repos
        
        # Create a monitor that's overdue (last ping 10 minutes ago, interval 5 minutes)
        overdue_monitor = Monitor(
            id=1,
            name="Test Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now() - timedelta(minutes=10),
            email_recipient="test@example.com",
            webhook_url=None,
            expires_at=None
        )
        
        monitor_repo.get_all.return_value = [overdue_monitor]
        
        # Mock alert methods
        with patch.object(monitor_service, 'send_alert_email') as mock_email:
            monitor_service.check_missed_pings()
            
            # Should detect overdue and send email
            mock_email.assert_called_once_with(overdue_monitor)
            
            # Should update last_ping
            monitor_repo.update_last_ping.assert_called_once()
    
    def test_check_missed_pings_ignores_on_time_monitor(self, monitor_service, mock_repos):
        """Test that monitors with recent pings are not flagged"""
        monitor_repo, _, _ = mock_repos
        
        # Create a monitor that's on time (last ping 2 minutes ago, interval 5 minutes)
        on_time_monitor = Monitor(
            id=1,
            name="Test Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now() - timedelta(minutes=2),
            email_recipient="test@example.com",
            webhook_url=None,
            expires_at=None
        )
        
        monitor_repo.get_all.return_value = [on_time_monitor]
        
        # Mock alert methods
        with patch.object(monitor_service, 'send_alert_email') as mock_email:
            with patch.object(monitor_service, 'send_webhook_alert') as mock_webhook:
                monitor_service.check_missed_pings()
                
                # Should NOT send any alerts
                mock_email.assert_not_called()
                mock_webhook.assert_not_called()
                
                # Should NOT update last_ping
                monitor_repo.update_last_ping.assert_not_called()
    
    def test_check_missed_pings_skips_monitors_without_last_ping(self, monitor_service, mock_repos):
        """Test that monitors without a last_ping are skipped"""
        monitor_repo, _, _ = mock_repos
        
        # Create a monitor without last_ping (newly created)
        new_monitor = Monitor(
            id=1,
            name="New Monitor",
            interval=5.0,
            user_id=1,
            last_ping=None,  # Never pinged
            email_recipient="test@example.com",
            webhook_url=None,
            expires_at=None
        )
        
        monitor_repo.get_all.return_value = [new_monitor]
        
        # Mock alert methods
        with patch.object(monitor_service, 'send_alert_email') as mock_email:
            monitor_service.check_missed_pings()
            
            # Should skip this monitor
            mock_email.assert_not_called()
            monitor_repo.update_last_ping.assert_not_called()
    
    def test_check_missed_pings_skips_expired_monitors(self, monitor_service, mock_repos):
        """Test that expired monitors are not checked"""
        monitor_repo, _, _ = mock_repos
        
        # Create an expired monitor that would otherwise be overdue
        expired_monitor = Monitor(
            id=1,
            name="Expired Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now() - timedelta(minutes=10),
            email_recipient="test@example.com",
            webhook_url=None,
            expires_at=datetime.now() - timedelta(days=1)  # Expired yesterday
        )
        
        monitor_repo.get_all.return_value = [expired_monitor]
        
        # Mock alert methods
        with patch.object(monitor_service, 'send_alert_email') as mock_email:
            monitor_service.check_missed_pings()
            
            # Should skip expired monitor
            mock_email.assert_not_called()
            monitor_repo.update_last_ping.assert_not_called()
    
    def test_check_missed_pings_sends_webhook_alerts(self, monitor_service, mock_repos):
        """Test that webhook alerts are sent for monitors with webhook URLs"""
        monitor_repo, _, _ = mock_repos
        
        # Create overdue monitor with webhook
        overdue_monitor = Monitor(
            id=1,
            name="Webhook Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now() - timedelta(minutes=10),
            email_recipient=None,
            webhook_url="https://example.com/webhook",
            expires_at=None
        )
        
        monitor_repo.get_all.return_value = [overdue_monitor]
        
        # Mock webhook sending
        with patch.object(monitor_service, 'send_webhook_alert') as mock_webhook:
            monitor_service.check_missed_pings()
            
            # Should send webhook alert
            mock_webhook.assert_called_once_with(overdue_monitor)
            
            # Should update last_ping
            monitor_repo.update_last_ping.assert_called_once()
    
    def test_check_missed_pings_sends_both_email_and_webhook(self, monitor_service, mock_repos):
        """Test that both email and webhook alerts are sent when configured"""
        monitor_repo, _, _ = mock_repos
        
        # Create overdue monitor with both email and webhook
        overdue_monitor = Monitor(
            id=1,
            name="Dual Alert Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now() - timedelta(minutes=10),
            email_recipient="test@example.com",
            webhook_url="https://example.com/webhook",
            expires_at=None
        )
        
        monitor_repo.get_all.return_value = [overdue_monitor]
        
        # Mock both alert methods
        with patch.object(monitor_service, 'send_alert_email') as mock_email:
            with patch.object(monitor_service, 'send_webhook_alert') as mock_webhook:
                monitor_service.check_missed_pings()
                
                # Should send both alerts
                mock_email.assert_called_once_with(overdue_monitor)
                mock_webhook.assert_called_once_with(overdue_monitor)
    
    def test_check_missed_pings_handles_multiple_monitors(self, monitor_service, mock_repos):
        """Test checking multiple monitors in one run"""
        monitor_repo, _, _ = mock_repos
        
        # Create multiple monitors with different states
        overdue1 = Monitor(
            id=1,
            name="Overdue 1",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now() - timedelta(minutes=10),
            email_recipient="test1@example.com",
            webhook_url=None,
            expires_at=None
        )
        
        on_time = Monitor(
            id=2,
            name="On Time",
            interval=10.0,
            user_id=1,
            last_ping=datetime.now() - timedelta(minutes=5),
            email_recipient="test2@example.com",
            webhook_url=None,
            expires_at=None
        )
        
        overdue2 = Monitor(
            id=3,
            name="Overdue 2",
            interval=5.0,
            user_id=2,
            last_ping=datetime.now() - timedelta(minutes=15),
            email_recipient="test3@example.com",
            webhook_url=None,
            expires_at=None
        )
        
        monitor_repo.get_all.return_value = [overdue1, on_time, overdue2]
        
        # Mock alert methods
        with patch.object(monitor_service, 'send_alert_email') as mock_email:
            monitor_service.check_missed_pings()
            
            # Should send alerts for 2 overdue monitors
            assert mock_email.call_count == 2
            mock_email.assert_any_call(overdue1)
            mock_email.assert_any_call(overdue2)
            
            # Should update last_ping for overdue monitors only
            assert monitor_repo.update_last_ping.call_count == 2
    
    @patch('api.services.monitor_service.requests.post')
    def test_send_webhook_alert_success(self, mock_post, monitor_service):
        """Test successful webhook alert sending"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        monitor = Monitor(
            id=1,
            name="Test Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now() - timedelta(minutes=10),
            email_recipient=None,
            webhook_url="https://example.com/webhook",
            expires_at=None
        )
        
        monitor_service.send_webhook_alert(monitor)
        
        # Verify webhook was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL
        assert call_args[0][0] == "https://example.com/webhook"
        
        # Check payload
        payload = call_args[1]['json']
        assert payload['event'] == 'monitor_missed_ping'
        assert payload['monitor_name'] == 'Test Monitor'
        assert payload['interval_minutes'] == 5.0
    
    @patch('api.services.monitor_service.requests.post')
    def test_send_webhook_alert_handles_failure(self, mock_post, monitor_service):
        """Test webhook alert handles HTTP errors gracefully"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        monitor = Monitor(
            id=1,
            name="Test Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now(),
            email_recipient=None,
            webhook_url="https://example.com/webhook",
            expires_at=None
        )
        
        # Should not raise exception
        monitor_service.send_webhook_alert(monitor)
        
        # Webhook should have been attempted
        mock_post.assert_called_once()
    
    @patch('api.services.monitor_service.requests.post')
    def test_send_webhook_alert_handles_network_error(self, mock_post, monitor_service):
        """Test webhook alert handles network errors gracefully"""
        import requests
        mock_post.side_effect = requests.RequestException("Connection refused")
        
        monitor = Monitor(
            id=1,
            name="Test Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now(),
            email_recipient=None,
            webhook_url="https://example.com/webhook",
            expires_at=None
        )
        
        # Should not raise exception
        monitor_service.send_webhook_alert(monitor)
        
        # Webhook should have been attempted
        mock_post.assert_called_once()
    
    def test_send_alert_email_skips_if_no_email_service(self, monitor_service):
        """Test that email alerts are skipped when email service is not configured"""
        monitor = Monitor(
            id=1,
            name="Test Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now(),
            email_recipient="test@example.com",
            webhook_url=None,
            expires_at=None
        )
        
        # email_service is None by default in our mock setup
        monitor_service.send_alert_email(monitor)
        
        # Should not raise exception, just log and skip
    
    def test_send_alert_email_skips_expired_monitors(self, monitor_service):
        """Test that email alerts are not sent for expired monitors"""
        # Mock email service
        mock_email_service = Mock()
        monitor_service.email_service = mock_email_service
        
        expired_monitor = Monitor(
            id=1,
            name="Expired Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now(),
            email_recipient="test@example.com",
            webhook_url=None,
            expires_at=datetime.utcnow() - timedelta(days=1)  # Expired
        )
        
        monitor_service.send_alert_email(expired_monitor)
        
        # Should NOT send email
        mock_email_service.send_alert.assert_not_called()
    
    def test_send_alert_email_skips_if_no_recipient(self, monitor_service):
        """Test that email alerts are skipped when no recipient is configured"""
        # Mock email service
        mock_email_service = Mock()
        monitor_service.email_service = mock_email_service
        
        monitor = Monitor(
            id=1,
            name="Test Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now(),
            email_recipient=None,  # No recipient
            webhook_url=None,
            expires_at=None
        )
        
        monitor_service.send_alert_email(monitor)
        
        # Should NOT send email
        mock_email_service.send_alert.assert_not_called()
    
    def test_send_alert_email_success(self, monitor_service):
        """Test successful email alert sending"""
        # Mock email service
        mock_email_service = Mock()
        mock_email_service.send_alert.return_value = (True, "Email sent successfully")
        monitor_service.email_service = mock_email_service
        
        monitor = Monitor(
            id=1,
            name="Test Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now() - timedelta(minutes=10),
            email_recipient="test@example.com",
            webhook_url=None,
            expires_at=None
        )
        
        monitor_service.send_alert_email(monitor)
        
        # Should send email
        mock_email_service.send_alert.assert_called_once()
        
        # Verify email content
        call_args = mock_email_service.send_alert.call_args[1]
        assert call_args['to_email'] == "test@example.com"
        assert "Test Monitor" in call_args['subject']
        assert "missed ping" in call_args['subject'].lower()
        assert "Test Monitor" in call_args['html_content']
    
    def test_ping_monitor_updates_last_ping(self, monitor_service, mock_repos):
        """Test that pinging a monitor updates its last_ping time"""
        monitor_repo, _, _ = mock_repos
        
        monitor = Monitor(
            id=1,
            name="Test Monitor",
            interval=5.0,
            user_id=1,
            last_ping=datetime.now() - timedelta(minutes=3),
            email_recipient="test@example.com",
            webhook_url=None,
            expires_at=None
        )
        
        monitor_repo.get_by_id.return_value = monitor
        
        result = monitor_service.ping_monitor(1, 1)
        
        # Should find monitor
        monitor_repo.get_by_id.assert_called_once_with(1, 1)
        
        # Should update last_ping
        monitor_repo.update_last_ping.assert_called_once()
        
        # Should return success
        assert result['status'] == 'success'
        assert result['monitor_id'] == 1
    
    def test_ping_monitor_raises_for_nonexistent_monitor(self, monitor_service, mock_repos):
        """Test that pinging a non-existent monitor raises an error"""
        monitor_repo, _, _ = mock_repos
        monitor_repo.get_by_id.return_value = None
        
        with pytest.raises(ValueError, match="Monitor not found"):
            monitor_service.ping_monitor(999, 1)
