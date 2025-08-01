"""add booking system and accommodation pricing

Revision ID: 0c3d2f2b2565
Revises: 85ab4b44e7e0
Create Date: 2025-07-29 13:58:59.443875

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0c3d2f2b2565"
down_revision: Union[str, Sequence[str], None] = "85ab4b44e7e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("accommodation_id", sa.Integer(), nullable=False),
        sa.Column("check_in_date", sa.Date(), nullable=True),
        sa.Column("check_out_date", sa.Date(), nullable=True),
        sa.Column("is_open_dates", sa.Boolean(), nullable=False),
        sa.Column("actual_check_in", sa.DateTime(), nullable=True),
        sa.Column("actual_check_out", sa.DateTime(), nullable=True),
        sa.Column("guests_count", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "CONFIRMED",
                "CHECKED_IN",
                "CHECKED_OUT",
                "CANCELLED",
                name="bookingstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            sa.Enum("NOT_PAID", "PARTIAL", "PAID", name="paymentstatus"),
            nullable=False,
        ),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["accommodation_id"],
            ["accommodations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bookings_id"), "bookings", ["id"], unique=False)
    op.add_column(
        "accommodations",
        sa.Column("price_per_night", sa.Numeric(precision=10, scale=2), nullable=False),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("accommodations", "price_per_night")
    op.drop_index(op.f("ix_bookings_id"), table_name="bookings")
    op.drop_table("bookings")
    # ### end Alembic commands ###
