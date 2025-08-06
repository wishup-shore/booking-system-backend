#!/usr/bin/env python3
"""
Script to create an admin user (staff role) for the booking system.
Run this script to create the first administrative user.
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole


async def create_admin_user():
    print("🔧 Creating admin user for Booking System")
    print("-" * 40)

    # Get user input
    username = input("Enter admin username: ").strip()
    if not username:
        print("❌ Username cannot be empty")
        return False

    email = input("Enter admin email: ").strip()
    if not email:
        print("❌ Email cannot be empty")
        return False

    password = input("Enter admin password: ").strip()
    if not password:
        print("❌ Password cannot be empty")
        return False

    # Confirm password
    password_confirm = input("Confirm password: ").strip()
    if password != password_confirm:
        print("❌ Passwords do not match")
        return False

    if len(password) < 6:
        print("❌ Password must be at least 6 characters long")
        return False

    # Create async database session
    async with AsyncSessionLocal() as db:
        try:
            # Check if user already exists
            existing_user_stmt = select(User).where(
                (User.username == username) | (User.email == email)
            )
            existing_user_result = await db.execute(existing_user_stmt)
            existing_user = existing_user_result.scalar_one_or_none()

            if existing_user:
                print(
                    f"❌ User with username '{username}' or email '{email}' already exists"
                )
                return False

            # Create new admin user
            hashed_password = get_password_hash(password)
            admin_user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                role=UserRole.STAFF,  # Highest permission role
                is_active=True,
            )

            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)

            print("✅ Admin user created successfully!")
            print(f"   Username: {admin_user.username}")
            print(f"   Email: {admin_user.email}")
            print(f"   Role: {admin_user.role.value}")
            print(f"   User ID: {admin_user.id}")
            print()
            print("🚀 You can now login to the system with these credentials.")

            return True

        except Exception as e:
            print(f"❌ Error creating admin user: {str(e)}")
            await db.rollback()
            return False


async def main():
    print("=" * 50)
    print("🏠 BOOKING SYSTEM - ADMIN USER CREATOR")
    print("=" * 50)
    print()

    try:
        success = await create_admin_user()
        if success:
            print("\n" + "=" * 50)
            print("✅ SETUP COMPLETE!")
            print("=" * 50)
            sys.exit(0)
        else:
            print("\n" + "=" * 50)
            print("❌ SETUP FAILED!")
            print("=" * 50)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
