import streamlit as st
from app.streamlit_pages.components.auth import auth

st.set_page_config(
    page_title="Booking System Dashboard",
    page_icon="🏠",
    layout="wide"
)

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
    
    # Main dashboard content
    st.header("Welcome to the Booking System")
    
    # Get user info
    user_info = auth.get_user_info()
    if user_info:
        st.write(f"Hello, **{user_info['username']}**! Your role is **{user_info['role']}**.")
    
    # Dashboard stats (placeholder for now)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total Accommodations",
            value="0",
            help="Total number of accommodations in the system"
        )
    
    with col2:
        st.metric(
            label="Available",
            value="0",
            help="Currently available accommodations"
        )
    
    with col3:
        st.metric(
            label="Occupied",
            value="0",
            help="Currently occupied accommodations"
        )
    
    st.markdown("---")
    
    # Quick actions
    st.subheader("Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 Manage Accommodations", type="primary"):
            st.switch_page("pages/02_Accommodations.py")
    
    with col2:
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