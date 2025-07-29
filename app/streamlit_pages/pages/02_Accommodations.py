import streamlit as st
import requests
import pandas as pd
from app.streamlit_pages.components.auth import auth

st.set_page_config(
    page_title="Accommodations Management",
    page_icon="🏨",
    layout="wide"
)

API_BASE_URL = "http://localhost:8000/api/v1"

def get_accommodation_types():
    """Fetch accommodation types from API"""
    try:
        headers = auth.get_headers()
        response = requests.get(f"{API_BASE_URL}/accommodation-types/", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_accommodations():
    """Fetch accommodations from API"""
    try:
        headers = auth.get_headers()
        response = requests.get(f"{API_BASE_URL}/accommodations/", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def create_accommodation_type(data):
    """Create new accommodation type"""
    try:
        headers = auth.get_headers()
        response = requests.post(f"{API_BASE_URL}/accommodation-types/", 
                                json=data, headers=headers)
        return response.status_code == 200
    except:
        return False

def create_accommodation(data):
    """Create new accommodation"""
    try:
        headers = auth.get_headers()
        response = requests.post(f"{API_BASE_URL}/accommodations/", 
                                json=data, headers=headers)
        return response.status_code == 200
    except:
        return False

def update_accommodation(accommodation_id, data):
    """Update accommodation"""
    try:
        headers = auth.get_headers()
        response = requests.put(f"{API_BASE_URL}/accommodations/{accommodation_id}", 
                               json=data, headers=headers)
        return response.status_code == 200
    except:
        return False

def delete_accommodation(accommodation_id):
    """Delete accommodation"""
    try:
        headers = auth.get_headers()
        response = requests.delete(f"{API_BASE_URL}/accommodations/{accommodation_id}", 
                                  headers=headers)
        return response.status_code == 200
    except:
        return False

def main():
    st.title("🏨 Accommodations Management")
    
    # Check authentication
    if not auth.is_authenticated():
        st.error("Please login first")
        if st.button("Go to Login"):
            st.switch_page("01_Dashboard.py")
        return
    
    # Show user info in sidebar
    auth.render_user_info()
    
    # Navigation in sidebar
    st.sidebar.title("Navigation")
    
    if st.sidebar.button("🏠 Dashboard"):
        st.switch_page("01_Dashboard.py")
    
    if st.sidebar.button("🏨 Accommodations", type="primary"):
        st.switch_page("pages/02_Accommodations.py")
    
    if st.sidebar.button("👥 Clients"):
        st.switch_page("pages/03_Clients.py")
    
    if st.sidebar.button("📅 Bookings"):
        st.switch_page("pages/04_Bookings.py")
    
    # Check user role for write operations
    user_info = auth.get_user_info()
    is_staff = user_info and user_info.get('role') == 'staff'
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📋 View Accommodations", "🏗️ Accommodation Types", "➕ Add New"])
    
    with tab1:
        st.header("Current Accommodations")
        
        # Fetch and display accommodations
        accommodations = get_accommodations()
        
        if accommodations:
            # Convert to DataFrame for better display
            df_data = []
            for acc in accommodations:
                df_data.append({
                    "ID": acc["id"],
                    "Number": acc["number"],
                    "Type": acc["type"]["name"],
                    "Capacity": acc["capacity"],
                    "Price/Night": f"${float(acc.get('price_per_night', 0)):.2f}",
                    "Status": acc["status"],
                    "Condition": acc["condition"],
                    "Comments": acc.get("comments", "")[:50] + "..." if acc.get("comments", "") and len(acc.get("comments", "")) > 50 else acc.get("comments", "")
                })
            
            df = pd.DataFrame(df_data)
            
            # Display dataframe for all users
            st.dataframe(df, use_container_width=True)
            
            # Display editing capabilities for staff
            if is_staff:
                st.markdown("---")
                st.write("**Edit Accommodations:**")
                
                # Use selectbox for editing
                accommodation_options = {f"{acc['number']} - {acc['type']['name']} ({acc['status']})": i for i, acc in enumerate(accommodations)}
                
                if accommodation_options:
                    selected_display = st.selectbox("Choose accommodation to edit:", [""] + list(accommodation_options.keys()))
                    
                    if selected_display:
                        selected_idx = accommodation_options[selected_display]
                        selected_acc = accommodations[selected_idx]
                        
                        st.subheader(f"Edit Accommodation {selected_acc['number']}")
                        
                        with st.form(f"edit_accommodation_{selected_acc['id']}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                new_number = st.text_input("Number", value=selected_acc["number"])
                                new_capacity = st.number_input("Capacity", value=selected_acc["capacity"], min_value=1)
                                new_price = st.number_input("Price per Night ($)", 
                                                          value=float(selected_acc.get("price_per_night", 0)),
                                                          min_value=0.0,
                                                          step=1.0,
                                                          help="Price in dollars per night")
                                new_status = st.selectbox("Status", 
                                                        ["available", "occupied", "maintenance", "out_of_order"],
                                                        index=["available", "occupied", "maintenance", "out_of_order"].index(selected_acc["status"]))
                            
                            with col2:
                                new_condition = st.selectbox("Condition", 
                                                           ["ok", "minor", "critical"],
                                                           index=["ok", "minor", "critical"].index(selected_acc["condition"]))
                                new_comments = st.text_area("Comments", value=selected_acc.get("comments", ""))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Update", type="primary"):
                                    update_data = {
                                        "number": new_number,
                                        "capacity": new_capacity,
                                        "price_per_night": new_price,
                                        "status": new_status,
                                        "condition": new_condition,
                                        "comments": new_comments
                                    }
                                    
                                    if update_accommodation(selected_acc["id"], update_data):
                                        st.success("Accommodation updated successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to update accommodation")
                            
                            with col2:
                                if st.form_submit_button("Delete", type="secondary"):
                                    if delete_accommodation(selected_acc["id"]):
                                        st.success("Accommodation deleted successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete accommodation")
            else:
                st.info("Staff role required for editing accommodations")
        else:
            st.info("No accommodations found")
    
    with tab2:
        st.header("Accommodation Types")
        
        # Fetch and display accommodation types
        acc_types = get_accommodation_types()
        
        if acc_types:
            for acc_type in acc_types:
                with st.expander(f"{acc_type['name']} (Default capacity: {acc_type['default_capacity']})"):
                    st.write(f"**Description:** {acc_type.get('description', 'No description')}")
                    st.write(f"**Active:** {'Yes' if acc_type['is_active'] else 'No'}")
                    st.write(f"**Created:** {acc_type['created_at']}")
        else:
            st.info("No accommodation types found")
        
        # Add new accommodation type (staff only)
        if is_staff:
            st.subheader("Add New Accommodation Type")
            
            with st.form("add_accommodation_type"):
                col1, col2 = st.columns(2)
                
                with col1:
                    type_name = st.text_input("Type Name", placeholder="e.g., Палатка, Домик, Коттедж")
                    default_capacity = st.number_input("Default Capacity", min_value=1, value=2)
                
                with col2:
                    description = st.text_area("Description", placeholder="Optional description")
                    is_active = st.checkbox("Active", value=True)
                
                if st.form_submit_button("Create Type", type="primary"):
                    if type_name:
                        type_data = {
                            "name": type_name,
                            "description": description or None,
                            "default_capacity": default_capacity,
                            "is_active": is_active
                        }
                        
                        if create_accommodation_type(type_data):
                            st.success("Accommodation type created successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to create accommodation type")
                    else:
                        st.error("Type name is required")
        else:
            st.info("Staff role required for creating accommodation types")
    
    with tab3:
        st.header("Add New Accommodation")
        
        if not is_staff:
            st.info("Staff role required for adding accommodations")
            return
        
        acc_types = get_accommodation_types()
        
        if not acc_types:
            st.warning("Please create accommodation types first")
            return
        
        with st.form("add_accommodation"):
            col1, col2 = st.columns(2)
            
            with col1:
                acc_number = st.text_input("Accommodation Number", placeholder="e.g., T001, H101")
                
                type_options = {f"{t['name']} (cap: {t['default_capacity']})": t for t in acc_types if t['is_active']}
                selected_type_display = st.selectbox("Type", list(type_options.keys()))
                selected_type = type_options[selected_type_display] if selected_type_display else None
                
                capacity = st.number_input("Capacity", 
                                         min_value=1, 
                                         value=selected_type["default_capacity"] if selected_type else 2)
                
                price_per_night = st.number_input("Price per Night ($)", 
                                                min_value=0.0, 
                                                value=50.0,
                                                step=1.0,
                                                help="Price in dollars per night")
            
            with col2:
                status = st.selectbox("Initial Status", 
                                    ["available", "occupied", "maintenance", "out_of_order"],
                                    index=0)
                condition = st.selectbox("Initial Condition", 
                                       ["ok", "minor", "critical"],
                                       index=0)
                comments = st.text_area("Comments", placeholder="Optional initial comments")
            
            if st.form_submit_button("Create Accommodation", type="primary"):
                if acc_number and selected_type:
                    acc_data = {
                        "number": acc_number,
                        "type_id": selected_type["id"],
                        "capacity": capacity,
                        "price_per_night": price_per_night,
                        "status": status,
                        "condition": condition,
                        "comments": comments or None
                    }
                    
                    if create_accommodation(acc_data):
                        st.success("Accommodation created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create accommodation. Number might already exist.")
                else:
                    st.error("Number and type are required")

if __name__ == "__main__":
    main()