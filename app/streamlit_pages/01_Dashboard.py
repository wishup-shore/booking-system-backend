import streamlit as st
import requests
from datetime import date, timedelta
from app.streamlit_pages.components.auth import auth

st.set_page_config(
    page_title="Booking System Dashboard",
    page_icon="🏠",
    layout="wide"
)

API_BASE_URL = "http://localhost:8000/api/v1"

def get_dashboard_stats():
    """Fetch dashboard statistics"""
    stats = {
        'total_accommodations': 0,
        'total_clients': 0,
        'active_bookings': 0,
        'open_bookings': 0,
        'today_checkins': 0,
        'today_checkouts': 0,
        'occupancy_rate': 0.0,
        'revenue_today': 0.0
    }
    
    try:
        headers = auth.get_headers()
        
        # Get accommodations count
        response = requests.get(f"{API_BASE_URL}/accommodations/", headers=headers, timeout=5)
        if response.status_code == 200:
            stats['total_accommodations'] = len(response.json())
        
        # Get clients count
        response = requests.get(f"{API_BASE_URL}/clients/", headers=headers, timeout=5)
        if response.status_code == 200:
            stats['total_clients'] = len(response.json())
        
        # Get active bookings count (confirmed + checked_in)
        for status in ['confirmed', 'checked_in']:
            response = requests.get(f"{API_BASE_URL}/bookings/", 
                                  headers=headers, params={'status': status}, timeout=5)
            if response.status_code == 200:
                stats['active_bookings'] += len(response.json())
        
        # Get open bookings count
        response = requests.get(f"{API_BASE_URL}/bookings/open", headers=headers, timeout=5)
        if response.status_code == 200:
            stats['open_bookings'] = len(response.json())
        
        # Get today's occupancy statistics
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        response = requests.get(f"{API_BASE_URL}/bookings/calendar/statistics",
                              headers=headers,
                              params={
                                  'start_date': today.isoformat(),
                                  'end_date': tomorrow.isoformat()
                              },
                              timeout=5)
        if response.status_code == 200:
            occupancy_data = response.json()
            stats['occupancy_rate'] = occupancy_data.get('occupancy_rate', 0.0)
            stats['revenue_today'] = occupancy_data.get('revenue', 0.0)
        
        # Get today's check-ins and check-outs (simplified - would need API enhancement for exact count)
        response = requests.get(f"{API_BASE_URL}/bookings/", headers=headers, timeout=5)
        if response.status_code == 200:
            bookings = response.json()
            today_str = today.isoformat()
            
            for booking in bookings:
                if booking.get('check_in_date') == today_str and booking['status'] in ['confirmed', 'checked_in']:
                    stats['today_checkins'] += 1
                if booking.get('check_out_date') == today_str and booking['status'] == 'checked_out':
                    stats['today_checkouts'] += 1
    
    except Exception as e:
        st.error(f"Error fetching dashboard stats: {e}")
    
    return stats

def main():
    st.title("🏠 Booking System Dashboard")
    
    # Handle authentication
    if not auth.is_authenticated():
        auth.render_login_form()
        return
    
    # Show user info in sidebar
    auth.render_user_info()
    
    # Navigation in sidebar
    st.sidebar.title("Navigation")
    
    if st.sidebar.button("🏠 Dashboard", type="primary"):
        st.switch_page("01_Dashboard.py")
    
    if st.sidebar.button("🏨 Accommodations"):
        st.switch_page("pages/02_Accommodations.py")
    
    if st.sidebar.button("👥 Clients"):
        st.switch_page("pages/03_Clients.py")
    
    if st.sidebar.button("📅 Bookings"):
        st.switch_page("pages/04_Bookings.py")
    
    # Main dashboard content
    st.header("Welcome to the Booking System")
    
    # Get user info
    user_info = auth.get_user_info()
    if user_info:
        st.write(f"Hello, **{user_info['username']}**! Your role is **{user_info['role']}**.")
    
    # Dashboard stats
    stats = get_dashboard_stats()
    
    # Main metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Accommodations",
            value=stats['total_accommodations'],
            help="Total number of accommodations in the system"
        )
    
    with col2:
        st.metric(
            label="Active Bookings", 
            value=stats['active_bookings'],
            help="Currently confirmed and checked-in bookings"
        )
    
    with col3:
        st.metric(
            label="Total Clients",
            value=stats['total_clients'],
            help="Total number of clients in the database"
        )
    
    with col4:
        st.metric(
            label="Occupancy Rate",
            value=f"{stats['occupancy_rate']:.1f}%",
            help="Today's occupancy rate"
        )
    
    # Secondary metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Open Bookings",
            value=stats['open_bookings'],
            help="Bookings without confirmed dates"
        )
    
    with col2:
        st.metric(
            label="Today's Check-ins",
            value=stats['today_checkins'],
            help="Bookings checking in today"
        )
    
    with col3:
        st.metric(
            label="Today's Check-outs", 
            value=stats['today_checkouts'],
            help="Bookings checking out today"
        )
    
    with col4:
        st.metric(
            label="Today's Revenue",
            value=f"${stats['revenue_today']:.2f}",
            help="Revenue generated today"
        )
    
    st.markdown("---")
    
    # Quick actions
    st.subheader("Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📅 Manage Bookings", type="primary"):
            st.switch_page("pages/04_Bookings.py")
    
    with col2:
        if st.button("🏨 Manage Accommodations"):
            st.switch_page("pages/02_Accommodations.py")
    
    with col3:
        if st.button("👥 Manage Clients"):
            st.switch_page("pages/03_Clients.py")
    
    with col4:
        if st.button("🔧 System Settings"):
            st.info("Settings page coming in future iterations")
    
    # System status
    st.markdown("---")
    st.subheader("System Status")
    
    # Check API connectivity
    try:
        import requests
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            st.success("✅ Backend API is running")
        else:
            st.error("❌ Backend API is not responding correctly")
    except:
        st.error("❌ Cannot connect to Backend API")
    
    # Check database connectivity (through API)
    try:
        headers = auth.get_headers()
        response = requests.get("http://localhost:8000/api/v1/accommodation-types/", 
                               headers=headers, timeout=5)
        if response.status_code in [200, 401, 403]:  # 401/403 means API is working, just auth issues
            st.success("✅ Database is accessible")
        else:
            st.error("❌ Database connection issues")
    except:
        st.error("❌ Cannot verify database connectivity")

if __name__ == "__main__":
    main()