"""add_search_performance_indexes

Revision ID: b10f24e7190b
Revises: 13b4e43ed9dc
Create Date: 2025-08-02 18:52:47.752375

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b10f24e7190b"
down_revision: Union[str, Sequence[str], None] = "13b4e43ed9dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with search performance indexes."""

    # Booking search performance indexes
    op.create_index(
        "idx_bookings_status_payment", "bookings", ["status", "payment_status"]
    )
    op.create_index(
        "idx_bookings_dates_range", "bookings", ["check_in_date", "check_out_date"]
    )
    op.create_index("idx_bookings_client_status", "bookings", ["client_id", "status"])
    op.create_index(
        "idx_bookings_accommodation_dates",
        "bookings",
        ["accommodation_id", "check_in_date", "check_out_date"],
    )
    op.create_index("idx_bookings_open_dates", "bookings", ["is_open_dates", "status"])
    op.create_index("idx_bookings_created_at", "bookings", ["created_at"])

    # Client search performance indexes
    op.create_index(
        "idx_clients_name_search",
        "clients",
        [sa.text("LOWER(first_name)"), sa.text("LOWER(last_name)")],
    )
    op.create_index("idx_clients_phone_search", "clients", ["phone"])
    op.create_index("idx_clients_email_search", "clients", [sa.text("LOWER(email)")])
    op.create_index("idx_clients_group_rating", "clients", ["group_id", "rating"])
    op.create_index("idx_clients_created_at", "clients", ["created_at"])

    # Accommodation search performance indexes
    op.create_index(
        "idx_accommodations_type_status", "accommodations", ["type_id", "status"]
    )
    op.create_index(
        "idx_accommodations_capacity_price",
        "accommodations",
        ["capacity", "price_per_night"],
    )
    op.create_index(
        "idx_accommodations_status_condition", "accommodations", ["status", "condition"]
    )

    # Inventory search performance indexes
    op.create_index(
        "idx_inventory_items_type_condition",
        "inventory_items",
        ["type_id", "condition"],
    )
    op.create_index(
        "idx_booking_inventory_booking", "booking_inventory", ["booking_id"]
    )
    op.create_index(
        "idx_booking_custom_items_booking", "booking_custom_items", ["booking_id"]
    )

    # Custom items search performance indexes
    op.create_index("idx_custom_items_active", "custom_items", ["is_active"])

    # Composite indexes for complex queries
    op.create_index(
        "idx_bookings_complex_search",
        "bookings",
        ["status", "payment_status", "check_in_date", "accommodation_id"],
    )


def downgrade() -> None:
    """Downgrade schema by removing search performance indexes."""

    # Remove composite indexes
    op.drop_index("idx_bookings_complex_search", table_name="bookings")

    # Remove custom items indexes
    op.drop_index("idx_custom_items_active", table_name="custom_items")

    # Remove inventory indexes
    op.drop_index("idx_booking_custom_items_booking", table_name="booking_custom_items")
    op.drop_index("idx_booking_inventory_booking", table_name="booking_inventory")
    op.drop_index("idx_inventory_items_type_condition", table_name="inventory_items")

    # Remove accommodation indexes
    op.drop_index("idx_accommodations_status_condition", table_name="accommodations")
    op.drop_index("idx_accommodations_capacity_price", table_name="accommodations")
    op.drop_index("idx_accommodations_type_status", table_name="accommodations")

    # Remove client indexes
    op.drop_index("idx_clients_created_at", table_name="clients")
    op.drop_index("idx_clients_group_rating", table_name="clients")
    op.drop_index("idx_clients_email_search", table_name="clients")
    op.drop_index("idx_clients_phone_search", table_name="clients")
    op.drop_index("idx_clients_name_search", table_name="clients")

    # Remove booking indexes
    op.drop_index("idx_bookings_created_at", table_name="bookings")
    op.drop_index("idx_bookings_open_dates", table_name="bookings")
    op.drop_index("idx_bookings_accommodation_dates", table_name="bookings")
    op.drop_index("idx_bookings_client_status", table_name="bookings")
    op.drop_index("idx_bookings_dates_range", table_name="bookings")
    op.drop_index("idx_bookings_status_payment", table_name="bookings")
