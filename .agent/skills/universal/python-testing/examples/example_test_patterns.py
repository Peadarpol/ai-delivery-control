"""
Example: Comprehensive Test Patterns

This example demonstrates best practices for pytest testing:
- AAA pattern (Arrange, Act, Assert)
- Fixtures and factories
- Parametrization
- Mocking
- Async testing
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest


class PaymentError(Exception):
    """Example custom exception."""

    pass


# =============================================================================
# BASIC TEST PATTERNS
# =============================================================================


class TestMemberService:
    """Example test class demonstrating core patterns."""

    def test_create_member_success(self, member_service, db_session):
        """
        Basic test following AAA pattern.

        Naming: test_[method]_[scenario]_[expected]
        """
        # Arrange
        member_data = {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "branch_id": 1,
        }

        # Act
        result = member_service.create_member(member_data)

        # Assert
        assert result.id is not None
        assert result.email == "test@example.com"
        assert result.status == "active"

    def test_create_member_duplicate_email_raises_error(
        self, member_service, existing_member
    ):
        """Test that duplicate email raises appropriate error."""
        # Arrange
        duplicate_data = {
            "email": existing_member.email,  # Same email
            "first_name": "Jane",
            "last_name": "Doe",
            "branch_id": 1,
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Email already exists"):
            member_service.create_member(duplicate_data)


# =============================================================================
# PARAMETRIZED TESTS
# =============================================================================


class TestMemberValidation:
    """Parametrized tests for validation logic."""

    @pytest.mark.parametrize(
        "email,is_valid",
        [
            ("valid@example.com", True),
            ("user.name@domain.co.uk", True),
            ("invalid-email", False),
            ("@nodomain.com", False),
            ("spaces in@email.com", False),
            ("", False),
            (None, False),
        ],
    )
    def test_email_validation(self, email, is_valid):
        """Test email validation with multiple inputs."""
        from src.domain.validators import validate_email

        if is_valid:
            assert validate_email(email) is True
        else:
            with pytest.raises(ValueError):
                validate_email(email)

    @pytest.mark.parametrize(
        "age,expected_status",
        [
            (14, "junior"),
            (18, "adult"),
            (65, "senior"),
            (10, pytest.param("invalid", marks=pytest.mark.xfail)),
        ],
    )
    def test_member_age_category(self, age, expected_status):
        """Test age-based member categorization."""
        from src.domain.member import get_age_category

        assert get_age_category(age) == expected_status


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def member_service(db_session, mock_email_service):
    """Create MemberService with mocked dependencies."""
    from src.application.services import MemberService

    return MemberService(db_session=db_session, email_service=mock_email_service)


@pytest.fixture
def mock_email_service():
    """Mock email service to avoid sending real emails."""
    service = Mock()
    service.send_welcome_email = Mock(return_value=True)
    service.send_verification_email = Mock(return_value=True)
    return service


@pytest.fixture
def existing_member(db_session, member_factory):
    """Create an existing member for duplicate tests."""
    return member_factory(
        email="existing@example.com", first_name="Existing", last_name="User"
    )


@pytest.fixture
def member_factory(db_session):
    """Factory for creating test members with custom attributes."""
    created = []

    def _create(**kwargs):
        defaults = {
            "email": f"test_{len(created)}@example.com",
            "first_name": "Test",
            "last_name": "User",
            "branch_id": 1,
            "status": "active",
        }
        defaults.update(kwargs)

        # Create member
        from src.infrastructure.database.models import Member

        member = Member(**defaults)
        db_session.add(member)
        db_session.commit()
        created.append(member)
        return member

    yield _create

    # Cleanup after test
    for member in created:
        db_session.delete(member)
    db_session.commit()


# =============================================================================
# MOCKING EXAMPLES
# =============================================================================


class TestPaymentService:
    """Tests demonstrating mocking patterns."""

    def test_process_payment_success(self, payment_service):
        """Mock external payment gateway."""
        with patch("src.services.payment.stripe") as mock_stripe:
            # Arrange
            mock_stripe.PaymentIntent.create.return_value = Mock(
                id="pi_123", status="succeeded"
            )

            # Act
            result = payment_service.process_payment(
                amount=5000,
                customer_id="cus_123",  # $50.00 in cents
            )

            # Assert
            assert result.success is True
            assert result.transaction_id == "pi_123"
            mock_stripe.PaymentIntent.create.assert_called_once_with(
                amount=5000, currency="aud", customer="cus_123"
            )

    def test_process_payment_gateway_error(self, payment_service):
        """Test handling of payment gateway errors."""
        with patch("src.services.payment.stripe") as mock_stripe:
            # Arrange - simulate gateway error
            mock_stripe.PaymentIntent.create.side_effect = Exception("Gateway timeout")

            # Act & Assert
            with pytest.raises(PaymentError, match="Gateway timeout"):
                payment_service.process_payment(amount=5000, customer_id="cus_123")


# =============================================================================
# ASYNC TESTS
# =============================================================================


class TestAsyncOperations:
    """Tests for async functions using pytest-asyncio."""

    @pytest.mark.asyncio
    async def test_fetch_member_data(self, async_member_service):
        """Test async member data fetching."""
        # Arrange
        member_id = 1

        # Act
        result = await async_member_service.get_member_async(member_id)

        # Assert
        assert result is not None
        assert result.id == member_id

    @pytest.mark.asyncio
    async def test_bulk_send_notifications(self, notification_service):
        """Test async bulk operations."""
        with patch.object(
            notification_service, "send_single", new_callable=AsyncMock
        ) as mock_send:
            # Arrange
            mock_send.return_value = True
            member_ids = [1, 2, 3, 4, 5]

            # Act
            results = await notification_service.send_bulk(
                member_ids=member_ids, message="Test notification"
            )

            # Assert
            assert len(results) == 5
            assert all(r is True for r in results)
            assert mock_send.call_count == 5


# =============================================================================
# EDGE CASES & ERROR HANDLING
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_list_handling(self, member_service):
        """Test handling of empty input."""
        result = member_service.search_members(filters={})
        assert result == []

    def test_null_optional_fields(self, member_factory):
        """Test that optional fields can be null."""
        member = member_factory(phone=None, emergency_contact=None)
        assert member.phone is None
        assert member.emergency_contact is None

    def test_maximum_field_length(self, member_service):
        """Test field length validation."""
        with pytest.raises(ValueError, match="exceeds maximum length"):
            member_service.create_member(
                {
                    "email": "test@example.com",
                    "first_name": "A" * 256,  # Exceeds 255 char limit
                    "last_name": "Doe",
                }
            )

    def test_concurrent_updates(self, member_service, existing_member, db_session):
        """Test optimistic locking for concurrent updates."""
        # Simulate another transaction updating the same record
        # This tests the concurrency control mechanism
        pass


# =============================================================================
# INTEGRATION TEST EXAMPLE
# =============================================================================


@pytest.mark.integration
class TestMemberRegistrationFlow:
    """Integration tests for complete user flows."""

    def test_complete_registration_flow(
        self,
        client,
        db_session,
        mock_email_service,  # TestClient
    ):
        """Test the complete member registration flow."""
        # Step 1: Register
        response = client.post(
            "/api/v1/members",
            json={
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "branch_id": 1,
            },
        )
        assert response.status_code == 201
        member_id = response.json()["id"]

        # Step 2: Verify email was sent
        mock_email_service.send_welcome_email.assert_called_once()

        # Step 3: Activate account
        response = client.post(f"/api/v1/members/{member_id}/activate")
        assert response.status_code == 200

        # Step 4: Verify final state
        response = client.get(f"/api/v1/members/{member_id}")
        assert response.json()["status"] == "active"
