import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
from app.streamlit_pages.components.auth import auth

st.set_page_config(
    page_title="Booking Management",
    page_icon="📅",
    layout="wide"
)

API_BASE_URL = "http://localhost:8000/api/v1"

def get_bookings(status=None):
    """Fetch bookings from API"""
    try:
        headers = auth.get_headers()
        params = {}
        if status:
            params["status"] = status
        
        response = requests.get(f"{API_BASE_URL}/bookings/", 
                              headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_open_bookings():
    """Fetch open-dates bookings"""
    try:
        headers = auth.get_headers()
        response = requests.get(f"{API_BASE_URL}/bookings/open", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_clients():
    """Fetch clients for booking creation"""
    try:
        headers = auth.get_headers()
        response = requests.get(f"{API_BASE_URL}/clients/", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_accommodations():
    """Fetch accommodations for booking creation"""
    try:
        headers = auth.get_headers()
        response = requests.get(f"{API_BASE_URL}/accommodations/", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_available_accommodations(start_date, end_date, capacity=None):
    """Get available accommodations for date range"""
    try:
        headers = auth.get_headers()
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        if capacity:
            params["capacity"] = capacity
        
        response = requests.get(f"{API_BASE_URL}/bookings/availability/accommodations", 
                              headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def create_booking(data):
    """Create new booking"""
    try:
        headers = auth.get_headers()
        response = requests.post(f"{API_BASE_URL}/bookings/", 
                                json=data, headers=headers)
        return response.status_code == 200, response.json() if response.status_code != 200 else None
    except Exception as e:
        return False, str(e)

def create_open_booking(data):
    """Create open-dates booking"""
    try:
        headers = auth.get_headers()
        response = requests.post(f"{API_BASE_URL}/bookings/open-dates", 
                                json=data, headers=headers)
        return response.status_code == 200, response.json() if response.status_code != 200 else None
    except Exception as e:
        return False, str(e)

def set_booking_dates(booking_id, start_date, end_date):
    """Set dates for open-dates booking"""
    try:
        headers = auth.get_headers()
        data = {
            "check_in_date": start_date.isoformat(),
            "check_out_date": end_date.isoformat()
        }
        response = requests.put(f"{API_BASE_URL}/bookings/{booking_id}/set-dates", 
                               json=data, headers=headers)
        return response.status_code == 200, response.json() if response.status_code != 200 else None
    except Exception as e:
        return False, str(e)

def process_checkin(booking_id, comments=""):
    """Process check-in"""
    try:
        headers = auth.get_headers()
        data = {"comments": comments}
        response = requests.post(f"{API_BASE_URL}/bookings/{booking_id}/checkin", 
                                json=data, headers=headers)
        return response.status_code == 200, response.json() if response.status_code != 200 else None
    except Exception as e:
        return False, str(e)

def process_checkout(booking_id, comments=""):
    """Process check-out"""
    try:
        headers = auth.get_headers()
        data = {"comments": comments}
        response = requests.post(f"{API_BASE_URL}/bookings/{booking_id}/checkout", 
                                json=data, headers=headers)
        return response.status_code == 200, response.json() if response.status_code != 200 else None
    except Exception as e:
        return False, str(e)

def add_payment(booking_id, amount, comments=""):
    """Add payment to booking"""
    try:
        headers = auth.get_headers()
        data = {
            "amount": float(amount),
            "comments": comments
        }
        response = requests.post(f"{API_BASE_URL}/bookings/{booking_id}/payment", 
                                json=data, headers=headers)
        return response.status_code == 200, response.json() if response.status_code != 200 else None
    except Exception as e:
        return False, str(e)

def get_calendar_occupancy(start_date, end_date):
    """Get calendar occupancy data"""
    try:
        headers = auth.get_headers()
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        response = requests.get(f"{API_BASE_URL}/bookings/calendar/occupancy", 
                              headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def render_booking_form():
    """Render booking creation form"""
    st.subheader("Create New Booking")
    
    # Booking type selection
    booking_type = st.radio(
        "Booking Type",
        ["Regular Booking", "Open Dates Booking"],
        help="Regular booking has specific dates, Open dates booking is flexible"
    )
    
    # Client selection
    clients = get_clients()
    if not clients:
        st.error("No clients found. Please add clients first.")
        return
    
    client_options = {f"{c['first_name']} {c['last_name']} - {c.get('phone', 'No phone')}": c['id'] 
                     for c in clients}
    selected_client_key = st.selectbox("Select Client", options=list(client_options.keys()))
    selected_client_id = client_options[selected_client_key]
    
    # Guest count
    guests_count = st.number_input("Number of Guests", min_value=1, max_value=20, value=2)
    
    # Comments
    comments = st.text_area("Comments", placeholder="Any special requests or notes...")
    
    if booking_type == "Regular Booking":
        # Date selection
        col1, col2 = st.columns(2)
        with col1:
            check_in = st.date_input("Check-in Date", 
                                   min_value=date.today(),
                                   value=date.today())
        with col2:
            check_out = st.date_input("Check-out Date", 
                                    min_value=check_in + timedelta(days=1),
                                    value=check_in + timedelta(days=2))
        
        if check_in >= check_out:
            st.error("Check-out date must be after check-in date")
            return
        
        # Show available accommodations
        available_accommodations = get_available_accommodations(check_in, check_out, guests_count)
        
        if not available_accommodations:
            st.warning("No accommodations available for the selected dates and capacity")
            return
        
        # Accommodation selection
        accommodation_options = {
            f"{acc['number']} - {acc['type_name']} (Capacity: {acc['capacity']}, Price: ${acc['price_per_night']}/night)": acc['id']
            for acc in available_accommodations
        }
        
        selected_acc_key = st.selectbox("Select Accommodation", options=list(accommodation_options.keys()))
        selected_acc_id = accommodation_options[selected_acc_key]
        
        # Calculate total
        nights = (check_out - check_in).days
        selected_acc = next(acc for acc in available_accommodations if acc['id'] == selected_acc_id)
        total_amount = nights * selected_acc['price_per_night']
        
        st.info(f"**Duration:** {nights} nights | **Total Amount:** ${total_amount:.2f}")
        
        if st.button("Create Regular Booking", type="primary"):
            booking_data = {
                "client_id": selected_client_id,
                "accommodation_id": selected_acc_id,
                "check_in_date": check_in.isoformat(),
                "check_out_date": check_out.isoformat(),
                "guests_count": guests_count,
                "comments": comments,
                "is_open_dates": False
            }
            
            success, error = create_booking(booking_data)
            if success:
                st.success("Booking created successfully!")
                st.rerun()
            else:
                st.error(f"Failed to create booking: {error}")
    
    else:  # Open Dates Booking
        # Accommodation selection (all accommodations)
        accommodations = get_accommodations()
        if not accommodations:
            st.error("No accommodations found.")
            return
        
        accommodation_options = {
            f"{acc['number']} - {acc['type']['name']} (Capacity: {acc['capacity']})": acc['id']
            for acc in accommodations if acc['capacity'] >= guests_count
        }
        
        if not accommodation_options:
            st.warning("No accommodations available with sufficient capacity")
            return
        
        selected_acc_key = st.selectbox("Select Accommodation", options=list(accommodation_options.keys()))
        selected_acc_id = accommodation_options[selected_acc_key]
        
        if st.button("Create Open Dates Booking", type="primary"):
            booking_data = {
                "client_id": selected_client_id,
                "accommodation_id": selected_acc_id,
                "guests_count": guests_count,
                "comments": comments
            }
            
            success, error = create_open_booking(booking_data)
            if success:
                st.success("Open dates booking created successfully!")
                st.rerun()
            else:
                st.error(f"Failed to create booking: {error}")

def render_bookings_list():
    """Render bookings list with management options"""
    st.subheader("Current Bookings")
    
    # Status filter
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "pending", "confirmed", "checked_in", "checked_out", "cancelled"]
    )
    
    # Fetch bookings
    bookings = get_bookings(None if status_filter == "All" else status_filter)
    
    if not bookings:
        st.info("No bookings found")
        return
    
    # Display bookings in cards
    for booking in bookings:
        with st.expander(
            f"#{booking['id']} - {booking.get('client', {}).get('first_name', 'Unknown')} "
            f"{booking.get('client', {}).get('last_name', '')} | "
            f"{booking.get('accommodation', {}).get('number', 'Unknown')} | "
            f"Status: {booking['status'].title()}"
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**Client Information:**")
                client = booking.get('client', {})
                st.write(f"Name: {client.get('first_name', '')} {client.get('last_name', '')}")
                st.write(f"Phone: {client.get('phone', 'N/A')}")
                st.write(f"Email: {client.get('email', 'N/A')}")
            
            with col2:
                st.write("**Booking Details:**")
                if booking['is_open_dates']:
                    st.write("**Type:** Open Dates")
                    if booking['check_in_date'] and booking['check_out_date']:
                        st.write(f"Dates: {booking['check_in_date']} to {booking['check_out_date']}")
                    else:
                        st.write("Dates: Not set")
                else:
                    st.write("**Type:** Regular")
                    st.write(f"Check-in: {booking['check_in_date']}")
                    st.write(f"Check-out: {booking['check_out_date']}")
                
                st.write(f"Guests: {booking['guests_count']}")
                accommodation = booking.get('accommodation', {})
                st.write(f"Accommodation: {accommodation.get('number', 'Unknown')}")
            
            with col3:
                st.write("**Payment Information:**")
                st.write(f"Total: ${booking['total_amount']}")
                st.write(f"Paid: ${booking['paid_amount']}")
                st.write(f"Status: {booking['payment_status'].replace('_', ' ').title()}")
                st.write(f"Balance: ${float(booking['total_amount']) - float(booking['paid_amount']):.2f}")
            
            # Management buttons (only for staff)
            user_info = auth.get_user_info()
            is_staff = user_info and user_info.get('role') == 'staff'
            
            if is_staff:
                st.write("**Actions:**")
                button_col1, button_col2, button_col3, button_col4 = st.columns(4)
                
                with button_col1:
                    if booking['status'] == 'confirmed' and st.button(f"Check-in #{booking['id']}", key=f"checkin_{booking['id']}"):
                        success, error = process_checkin(booking['id'])
                        if success:
                            st.success("Checked-in successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error: {error}")
                
                with button_col2:
                    if booking['status'] == 'checked_in' and st.button(f"Check-out #{booking['id']}", key=f"checkout_{booking['id']}"):
                        success, error = process_checkout(booking['id'])
                        if success:
                            st.success("Checked-out successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error: {error}")
                
                with button_col3:
                    if booking['is_open_dates'] and not booking['check_in_date']:
                        if st.button(f"Set Dates #{booking['id']}", key=f"setdates_{booking['id']}"):
                            st.session_state[f"show_dates_form_{booking['id']}"] = True
                
                with button_col4:
                    remaining_balance = float(booking['total_amount']) - float(booking['paid_amount'])
                    if remaining_balance > 0 and st.button(f"Add Payment #{booking['id']}", key=f"payment_{booking['id']}"):
                        st.session_state[f"show_payment_form_{booking['id']}"] = True
                
                # Set dates form
                if st.session_state.get(f"show_dates_form_{booking['id']}", False):
                    st.write("**Set Dates:**")
                    date_col1, date_col2, date_col3 = st.columns(3)
                    with date_col1:
                        new_checkin = st.date_input("Check-in Date", 
                                                  min_value=date.today(),
                                                  key=f"checkin_date_{booking['id']}")
                    with date_col2:
                        new_checkout = st.date_input("Check-out Date", 
                                                   min_value=new_checkin + timedelta(days=1),
                                                   key=f"checkout_date_{booking['id']}")
                    with date_col3:
                        if st.button("Set Dates", key=f"confirm_dates_{booking['id']}"):
                            success, error = set_booking_dates(booking['id'], new_checkin, new_checkout)
                            if success:
                                st.success("Dates set successfully!")
                                del st.session_state[f"show_dates_form_{booking['id']}"]
                                st.rerun()
                            else:
                                st.error(f"Error: {error}")
                
                # Payment form
                if st.session_state.get(f"show_payment_form_{booking['id']}", False):
                    st.write("**Add Payment:**")
                    payment_col1, payment_col2, payment_col3 = st.columns(3)
                    with payment_col1:
                        payment_amount = st.number_input("Amount", 
                                                       min_value=0.01, 
                                                       max_value=float(remaining_balance),
                                                       value=float(remaining_balance),
                                                       key=f"payment_amount_{booking['id']}")
                    with payment_col2:
                        payment_comments = st.text_input("Payment Note", 
                                                       key=f"payment_comments_{booking['id']}")
                    with payment_col3:
                        if st.button("Add Payment", key=f"confirm_payment_{booking['id']}"):
                            success, error = add_payment(booking['id'], payment_amount, payment_comments)
                            if success:
                                st.success("Payment added successfully!")
                                del st.session_state[f"show_payment_form_{booking['id']}"]
                                st.rerun()
                            else:
                                st.error(f"Error: {error}")

def render_open_bookings():
    """Render open-dates bookings management"""
    st.subheader("Open Dates Bookings")
    
    open_bookings = get_open_bookings()
    
    if not open_bookings:
        st.info("No open dates bookings found")
        return
    
    for booking in open_bookings:
        with st.expander(
            f"#{booking['id']} - {booking.get('client', {}).get('first_name', 'Unknown')} "
            f"{booking.get('client', {}).get('last_name', '')} | "
            f"{booking.get('accommodation', {}).get('number', 'Unknown')}"
        ):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Client Information:**")
                client = booking.get('client', {})
                st.write(f"Name: {client.get('first_name', '')} {client.get('last_name', '')}")
                st.write(f"Phone: {client.get('phone', 'N/A')}")
                st.write(f"Guests: {booking['guests_count']}")
            
            with col2:
                st.write("**Accommodation:**")
                accommodation = booking.get('accommodation', {})
                st.write(f"Number: {accommodation.get('number', 'Unknown')}")
                st.write(f"Type: {accommodation.get('type_name', 'Unknown')}")
                st.write(f"Capacity: {accommodation.get('capacity', 'Unknown')}")
            
            if booking.get('comments'):
                st.write(f"**Comments:** {booking['comments']}")

def render_calendar_view():
    """Render simplified calendar view"""
    st.subheader("Calendar Overview")
    
    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today())
    with col2:
        end_date = st.date_input("End Date", value=date.today() + timedelta(days=30))
    
    if start_date >= end_date:
        st.error("End date must be after start date")
        return
    
    # Get occupancy data
    occupancy_data = get_calendar_occupancy(start_date, end_date)
    
    if not occupancy_data:
        st.info("No occupancy data available for selected period")
        return
    
    # Create a simple calendar view
    calendar_data = []
    for day_data in occupancy_data:
        date_str = day_data['date']
        occupied_count = sum(1 for acc in day_data['accommodations'] if acc['is_occupied'])
        total_count = len(day_data['accommodations'])
        
        calendar_data.append({
            'Date': date_str,
            'Occupied': occupied_count,
            'Total': total_count,
            'Occupancy Rate': f"{(occupied_count/total_count*100):.1f}%" if total_count > 0 else "0%"
        })
    
    if calendar_data:
        df = pd.DataFrame(calendar_data)
        st.dataframe(df, use_container_width=True)
        
        # Show accommodation details for today if available
        today_str = date.today().isoformat()
        today_data = next((d for d in occupancy_data if d['date'] == today_str), None)
        
        if today_data:
            st.subheader(f"Today's Accommodations ({today_str})")
            
            occupied_accs = [acc for acc in today_data['accommodations'] if acc['is_occupied']]
            available_accs = [acc for acc in today_data['accommodations'] if not acc['is_occupied']]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Occupied:**")
                for acc in occupied_accs:
                    booking = acc.get('booking', {})
                    st.write(f"• {acc['number']} - {booking.get('client_name', 'Unknown')}")
            
            with col2:
                st.write("**Available:**")
                for acc in available_accs:
                    st.write(f"• {acc['number']} - {acc['type_name']}")

# Main app
def main():
    # Check authentication
    if not auth.is_authenticated():
        st.error("Please log in to access this page")
        if st.button("Go to Login"):
            st.switch_page("01_Dashboard.py")
        return
    
    # Show user info in sidebar
    auth.render_user_info()
    
    # Navigation in sidebar
    st.sidebar.title("Navigation")
    
    if st.sidebar.button("🏠 Dashboard"):
        st.switch_page("01_Dashboard.py")
    
    if st.sidebar.button("🏨 Accommodations"):
        st.switch_page("pages/02_Accommodations.py")
    
    if st.sidebar.button("👥 Clients"):
        st.switch_page("pages/03_Clients.py")
    
    if st.sidebar.button("📅 Bookings", type="primary"):
        st.switch_page("pages/04_Bookings.py")
    
    # Main content
    st.title("📅 Booking Management")
    st.markdown("Manage bookings, calendar, and reservations")
    
    # Check user role
    user_info = auth.get_user_info()
    is_staff = user_info and user_info.get('role') == 'staff'
    
    # Tabs for different sections
    if is_staff:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 All Bookings", "⏰ Open Dates", "📅 Calendar", "➕ New Booking", "📊 Statistics"])
    else:
        tab1, tab2, tab3 = st.tabs(["📋 All Bookings", "⏰ Open Dates", "📅 Calendar"])
    
    with tab1:
        render_bookings_list()
    
    with tab2:
        render_open_bookings()
    
    with tab3:
        render_calendar_view()
    
    if is_staff:
        with tab4:
            render_booking_form()
        
        with tab5:
            st.subheader("Booking Statistics")
            st.info("Statistics feature will be implemented in future iterations")

if __name__ == "__main__":
    main()