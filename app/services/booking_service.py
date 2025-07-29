from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from fastapi import HTTPException, status

from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.models.client import Client
from app.models.accommodation import Accommodation
from app.schemas.booking import (
    BookingCreate, BookingCreateOpenDates, BookingUpdate, BookingSetDates,
    BookingPayment, BookingCheckIn, BookingCheckOut, BookingWithDetails
)


class BookingService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Booking]:
        return (
            self.db.query(Booking)
            .options(joinedload(Booking.client), joinedload(Booking.accommodation))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_id(self, booking_id: int) -> Optional[Booking]:
        return (
            self.db.query(Booking)
            .options(joinedload(Booking.client), joinedload(Booking.accommodation))
            .filter(Booking.id == booking_id)
            .first()
        )
    
    def get_by_status(self, status: BookingStatus, skip: int = 0, limit: int = 100) -> List[Booking]:
        return (
            self.db.query(Booking)
            .options(joinedload(Booking.client), joinedload(Booking.accommodation))
            .filter(Booking.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_open_dates_bookings(self, skip: int = 0, limit: int = 100) -> List[Booking]:
        """Get all bookings with open dates"""
        return (
            self.db.query(Booking)
            .options(joinedload(Booking.client), joinedload(Booking.accommodation))
            .filter(Booking.is_open_dates == True)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_bookings_by_date_range(self, start_date: date, end_date: date) -> List[Booking]:
        """Get bookings within a date range"""
        return (
            self.db.query(Booking)
            .options(joinedload(Booking.client), joinedload(Booking.accommodation))
            .filter(
                and_(
                    Booking.is_open_dates == False,  # Only bookings with confirmed dates
                    or_(
                        and_(Booking.check_in_date <= end_date, Booking.check_out_date >= start_date),
                        and_(Booking.check_in_date >= start_date, Booking.check_in_date <= end_date),
                        and_(Booking.check_out_date >= start_date, Booking.check_out_date <= end_date)
                    )
                )
            )
            .all()
        )
    
    def check_availability(self, accommodation_id: int, check_in: date, check_out: date, 
                          exclude_booking_id: Optional[int] = None) -> bool:
        """Check if accommodation is available for given dates"""
        query = (
            self.db.query(Booking)
            .filter(
                and_(
                    Booking.accommodation_id == accommodation_id,
                    Booking.is_open_dates == False,  # Only bookings with confirmed dates
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]),
                    or_(
                        and_(Booking.check_in_date <= check_out, Booking.check_out_date >= check_in),
                        and_(Booking.check_in_date >= check_in, Booking.check_in_date <= check_out),
                        and_(Booking.check_out_date >= check_in, Booking.check_out_date <= check_out)
                    )
                )
            )
        )
        
        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)
        
        return query.count() == 0
    
    def create(self, booking_data: BookingCreate) -> Booking:
        # Validate client exists
        client = self.db.query(Client).filter(Client.id == booking_data.client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        # Validate accommodation exists
        accommodation = self.db.query(Accommodation).filter(
            Accommodation.id == booking_data.accommodation_id
        ).first()
        if not accommodation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accommodation not found"
            )
        
        # For regular bookings, check availability and validate dates
        if not booking_data.is_open_dates:
            if not booking_data.check_in_date or not booking_data.check_out_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Check-in and check-out dates are required for regular bookings"
                )
            
            if booking_data.check_in_date >= booking_data.check_out_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Check-out date must be after check-in date"
                )
            
            if not self.check_availability(accommodation.id, booking_data.check_in_date, booking_data.check_out_date):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Accommodation is not available for the selected dates"
                )
            
            # Calculate total amount based on nights and accommodation price
            nights = (booking_data.check_out_date - booking_data.check_in_date).days
            total_amount = accommodation.price_per_night * nights
        else:
            # For open dates bookings, no date validation needed
            total_amount = Decimal(0)
        
        db_booking = Booking(
            **booking_data.model_dump(),
            total_amount=total_amount,
            status=BookingStatus.PENDING
        )
        
        self.db.add(db_booking)
        self.db.commit()
        self.db.refresh(db_booking)
        return db_booking
    
    def create_open_dates(self, booking_data: BookingCreateOpenDates) -> Booking:
        """Create an open-dates booking"""
        regular_booking_data = BookingCreate(
            **booking_data.model_dump(),
            check_in_date=None,
            check_out_date=None,
            is_open_dates=True
        )
        return self.create(regular_booking_data)
    
    def update(self, booking_id: int, booking_data: BookingUpdate) -> Booking:
        db_booking = self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # If updating dates for a non-open-dates booking, check availability
        if (booking_data.check_in_date is not None or 
            booking_data.check_out_date is not None) and not db_booking.is_open_dates:
            
            new_check_in = booking_data.check_in_date or db_booking.check_in_date
            new_check_out = booking_data.check_out_date or db_booking.check_out_date
            new_accommodation_id = booking_data.accommodation_id or db_booking.accommodation_id
            
            if new_check_in >= new_check_out:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Check-out date must be after check-in date"
                )
            
            if not self.check_availability(new_accommodation_id, new_check_in, new_check_out, booking_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Accommodation is not available for the selected dates"
                )
        
        # Update fields
        update_data = booking_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_booking, field, value)
        
        # Recalculate total amount if dates or accommodation changed
        if (booking_data.check_in_date is not None or 
            booking_data.check_out_date is not None or
            booking_data.accommodation_id is not None) and not db_booking.is_open_dates:
            
            accommodation = self.db.query(Accommodation).filter(
                Accommodation.id == db_booking.accommodation_id
            ).first()
            if accommodation and db_booking.check_in_date and db_booking.check_out_date:
                nights = (db_booking.check_out_date - db_booking.check_in_date).days
                db_booking.total_amount = accommodation.price_per_night * nights
        
        self.db.commit()
        self.db.refresh(db_booking)
        return db_booking
    
    def set_dates(self, booking_id: int, dates_data: BookingSetDates) -> Booking:
        """Set dates for an open-dates booking"""
        db_booking = self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        if not db_booking.is_open_dates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only set dates for open-dates bookings"
            )
        
        if dates_data.check_in_date >= dates_data.check_out_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Check-out date must be after check-in date"
            )
        
        # Check availability
        if not self.check_availability(db_booking.accommodation_id, 
                                     dates_data.check_in_date, dates_data.check_out_date, booking_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Accommodation is not available for the selected dates"
            )
        
        # Update booking with dates
        db_booking.check_in_date = dates_data.check_in_date
        db_booking.check_out_date = dates_data.check_out_date
        db_booking.is_open_dates = False
        db_booking.status = BookingStatus.CONFIRMED
        
        # Calculate total amount
        accommodation = self.db.query(Accommodation).filter(
            Accommodation.id == db_booking.accommodation_id
        ).first()
        if accommodation:
            nights = (dates_data.check_out_date - dates_data.check_in_date).days
            db_booking.total_amount = accommodation.price_per_night * nights
        
        self.db.commit()
        self.db.refresh(db_booking)
        return db_booking
    
    def check_in(self, booking_id: int, checkin_data: BookingCheckIn) -> Booking:
        """Process check-in for a booking"""
        db_booking = self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        if db_booking.status != BookingStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only check-in confirmed bookings"
            )
        
        db_booking.status = BookingStatus.CHECKED_IN
        db_booking.actual_check_in = checkin_data.actual_check_in or datetime.utcnow()
        
        if checkin_data.comments:
            current_comments = db_booking.comments or ""
            db_booking.comments = f"{current_comments}\nCheck-in: {checkin_data.comments}".strip()
        
        self.db.commit()
        self.db.refresh(db_booking)
        return db_booking
    
    def check_out(self, booking_id: int, checkout_data: BookingCheckOut) -> Booking:
        """Process check-out for a booking"""
        db_booking = self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        if db_booking.status != BookingStatus.CHECKED_IN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only check-out checked-in bookings"
            )
        
        db_booking.status = BookingStatus.CHECKED_OUT
        db_booking.actual_check_out = checkout_data.actual_check_out or datetime.utcnow()
        
        if checkout_data.comments:
            current_comments = db_booking.comments or ""
            db_booking.comments = f"{current_comments}\nCheck-out: {checkout_data.comments}".strip()
        
        self.db.commit()
        self.db.refresh(db_booking)
        return db_booking
    
    def add_payment(self, booking_id: int, payment_data: BookingPayment) -> Booking:
        """Add payment to a booking"""
        db_booking = self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Add payment amount
        db_booking.paid_amount += payment_data.amount
        
        # Update payment status based on paid amount
        if db_booking.paid_amount >= db_booking.total_amount:
            db_booking.payment_status = PaymentStatus.PAID
        elif db_booking.paid_amount > 0:
            db_booking.payment_status = PaymentStatus.PARTIAL
        else:
            db_booking.payment_status = PaymentStatus.NOT_PAID
        
        # Add payment comment
        if payment_data.comments:
            current_comments = db_booking.comments or ""
            payment_note = f"Payment: +{payment_data.amount} - {payment_data.comments}"
            db_booking.comments = f"{current_comments}\n{payment_note}".strip()
        
        self.db.commit()
        self.db.refresh(db_booking)
        return db_booking
    
    def cancel(self, booking_id: int, reason: Optional[str] = None) -> Booking:
        """Cancel a booking"""
        db_booking = self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        if db_booking.status == BookingStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking is already cancelled"
            )
        
        if db_booking.status == BookingStatus.CHECKED_OUT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel completed bookings"
            )
        
        db_booking.status = BookingStatus.CANCELLED
        
        if reason:
            current_comments = db_booking.comments or ""
            db_booking.comments = f"{current_comments}\nCancelled: {reason}".strip()
        
        self.db.commit()
        self.db.refresh(db_booking)
        return db_booking
    
    def delete(self, booking_id: int) -> bool:
        """Delete a booking (only if not checked-in or checked-out)"""
        db_booking = self.get_by_id(booking_id)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        if db_booking.status in [BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete bookings that have been checked-in or completed"
            )
        
        self.db.delete(db_booking)
        self.db.commit()
        return True
    
    def get_with_details(self, booking_id: int) -> Optional[BookingWithDetails]:
        """Get booking with client and accommodation details"""
        booking = self.get_by_id(booking_id)
        if not booking:
            return None
        
        booking_dict = booking.__dict__.copy()
        
        # Add client details
        if booking.client:
            booking_dict['client'] = {
                'id': booking.client.id,
                'first_name': booking.client.first_name,
                'last_name': booking.client.last_name,
                'phone': booking.client.phone,
                'email': booking.client.email
            }
        
        # Add accommodation details
        if booking.accommodation:
            booking_dict['accommodation'] = {
                'id': booking.accommodation.id,
                'number': booking.accommodation.number,
                'type_name': booking.accommodation.type.name if booking.accommodation.type else None,
                'capacity': booking.accommodation.capacity,
                'price_per_night': float(booking.accommodation.price_per_night)
            }
        
        return BookingWithDetails.model_validate(booking_dict)